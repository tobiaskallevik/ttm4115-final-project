from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Restaurant, Order
from .serializers import RestaurantSerializer, OrderSerializer
import json
from .mqtt import client as mqtt_client

class RestaurantViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Restaurant.objects.all()
    serializer_class = RestaurantSerializer

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    ACTIVE_TRANSIT_PHASES = {'to_restaurant', 'to_customer'}
    RETURN_TO_CHARGING_PHASE = 'to_charging'
    RETURN_PHASE_TO_RESUME_PHASE = {
        'to_charging_from_restaurant': 'to_restaurant',
        'to_charging_from_customer': 'to_customer',
    }

    VALID_DRONE_ACTIONS = {
        'order',
        'at_dest_pickup',
        'pickup_complete',
        'at_dest_delivery',
        'presence_confirmed',
        'delivered',
        'low_battery',
        'routed_to_station',
        'cancel',
        'timeout',
        'package_stuck',
        'at_dest_charging',
        'resume_delivery',
    }

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        order = self.get_object()
        if order.status != 'pending':
            return Response(
                {'error': f'Order can only be accepted from "pending", current state is "{order.status}".'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        order.status = 'accepted'
        order.transit_phase = ''
        order.save(update_fields=['status', 'transit_phase'])
        return Response({'status': 'Order accepted'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def mark_ready(self, request, pk=None):
        order = self.get_object()
        if order.status != 'accepted':
            return Response(
                {'error': f'Order can only be marked ready from "accepted", current state is "{order.status}".'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        order.status = 'ready'
        order.transit_phase = ''
        order.save(update_fields=['status', 'transit_phase'])
        return Response({'status': 'Order marked ready for drone pickup'}, status=status.HTTP_200_OK)

   
    @action(detail=True, methods=['post'])
    def trigger_drone(self, request, pk=None):
        order = self.get_object()
        action = request.data.get('action')

        if order.status == 'delivered' and action != 'at_dest_charging':
            return Response({'status': 'Order already delivered', 'order_status': 'delivered'}, status=status.HTTP_200_OK)
        
        current_phase = order.transit_phase

        next_status = None
        next_phase = order.transit_phase

        if action == 'order' and order.status == 'ready':
            next_status = 'in_transit'
            next_phase = 'to_restaurant'
        elif action == 'at_dest_pickup' and order.status == 'in_transit' and order.transit_phase == 'to_restaurant':
            next_status = 'loaded'
            next_phase = ''
        elif action == 'pickup_complete' and order.status == 'loaded':
            next_status = 'in_transit'
            next_phase = 'to_customer'
        elif action == 'at_dest_delivery' and order.status == 'in_transit' and order.transit_phase == 'to_customer':
            next_status = 'arrived'
            next_phase = ''
        elif action == 'presence_confirmed' and order.status == 'arrived':
            next_status = 'delivering'
            next_phase = ''
        elif action == 'delivered' and order.status == 'delivering':
            next_status = 'delivered'
            next_phase = 'to_charging'
        elif action in ['cancel', 'timeout'] and order.status == 'arrived':
            next_status = 'failed'
            next_phase = ''
        elif action == 'low_battery' and order.status == 'in_transit' and order.transit_phase in self.ACTIVE_TRANSIT_PHASES:
            next_status = 'failed'
            if order.transit_phase == 'to_restaurant':
                next_phase = 'to_charging_from_restaurant'
            else:
                next_phase = 'to_charging_from_customer'
        elif action == 'package_stuck' and order.status in ['arrived', 'delivering']:
            next_status = 'stuck'
            next_phase = ''
        elif action == 'routed_to_station' and order.status in ['failed', 'stuck'] and order.transit_phase not in ({self.RETURN_TO_CHARGING_PHASE} | set(self.RETURN_PHASE_TO_RESUME_PHASE.keys())):
            next_status = order.status
            if order.transit_phase in self.ACTIVE_TRANSIT_PHASES:
                if order.transit_phase == 'to_restaurant':
                    next_phase = 'to_charging_from_restaurant'
                else:
                    next_phase = 'to_charging_from_customer'
            else:
                next_phase = self.RETURN_TO_CHARGING_PHASE
        elif action == 'at_dest_charging' and (
            (order.status == 'in_transit' and order.transit_phase in (self.ACTIVE_TRANSIT_PHASES | {self.RETURN_TO_CHARGING_PHASE} | set(self.RETURN_PHASE_TO_RESUME_PHASE.keys())))
            or order.status == 'delivered'
            or (order.status in ['failed', 'stuck'] and order.transit_phase in ({self.RETURN_TO_CHARGING_PHASE} | set(self.RETURN_PHASE_TO_RESUME_PHASE.keys())))
        ):
            next_status = order.status
            if order.transit_phase in self.RETURN_PHASE_TO_RESUME_PHASE:
                next_phase = order.transit_phase
            else:
                next_phase = ''
        elif action == 'resume_delivery' and order.status in ['failed', 'stuck', 'in_transit'] and order.transit_phase in self.RETURN_PHASE_TO_RESUME_PHASE:
            next_status = 'in_transit'
            next_phase = self.RETURN_PHASE_TO_RESUME_PHASE[order.transit_phase]
        elif action == 'error' and order.status in ['pending', 'accepted', 'ready', 'loaded', 'in_transit', 'arrived', 'delivering']:
            next_status = 'failed'
            next_phase = ''

        if next_status is None:
            return Response(
                {'error': f'Transition guard blocked action "{action}" from state "{order.status}"'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        order.status = next_status
        order.transit_phase = next_phase
        order.save(update_fields=['status', 'transit_phase'])
        
        
        publish_actions = [action]
        if action == 'low_battery':
            publish_actions.append('routed_to_station')
        elif action == 'resume_delivery':
            if current_phase == 'to_charging_from_restaurant':
                publish_actions = ['resume_to_restaurant']
            elif current_phase == 'to_charging_from_customer':
                publish_actions = ['resume_to_customer']
            else:
                publish_actions = ['order']

        for publish_action in publish_actions:
            payload = json.dumps({"action": publish_action, "id": order.id})
            result = mqtt_client.publish("drone", payload)
            if result.rc != 0:
                return Response(
                    {'error': f'Action accepted but MQTT publish failed while dispatching "{publish_action}" (rc={result.rc})'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
        return Response(
            {
                'status': f'Triggered {action}',
                'order_status': order.status,
                'transit_phase': order.transit_phase,
                'dispatched_actions': publish_actions,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=['post'])
    def trigger_drone_raw(self, request):
        action = request.data.get('action')
        order_id = request.data.get('id')

        if action not in self.VALID_DRONE_ACTIONS:
            return Response(
                {'error': f'Unsupported action "{action}"'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = {'action': action}
        if order_id is not None:
            payload['id'] = order_id

        result = mqtt_client.publish('drone', json.dumps(payload))
        if result.rc != 0:
            return Response(
                {'error': f'MQTT publish failed (rc={result.rc})'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response({'status': f'Triggered {action}'}, status=status.HTTP_200_OK)