import { useState, useEffect } from 'react';

const API_BASE = 'http://localhost:8000/api/orders';

function App() {
  const [order, setOrder] = useState<any>(null);

  const fetchOrder = async () => {
    try {
      const response = await fetch(`${API_BASE}/`);
      const data = await response.json();
      const active = data.filter((o: any) => o.status !== 'delivered').pop();
      setOrder(active || null);
    } catch (e) { console.error(e); }
  };

  useEffect(() => {
    fetchOrder();
    const interval = setInterval(fetchOrder, 1000);
    return () => clearInterval(interval);
  }, []);

  const trigger = async (action: string) => {
    if (!order) return;
    const res = await fetch(`${API_BASE}/${order.id}/trigger_drone/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action })
    });

    if (!res.ok) {
      const err = await res.json();
      alert(`Guard Blocked: ${err.error}`);
    } else {
      fetchOrder();
    }
  };

  const triggerRaw = async (action: string) => {
    const res = await fetch(`${API_BASE}/trigger_drone_raw/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action })
    });

    if (!res.ok) {
      const err = await res.json();
      alert(`Trigger Failed: ${err.error}`);
    }
  };

  if (!order) {
    return (
      <div style={{ padding: '20px', fontFamily: 'monospace', maxWidth: '800px', background: '#1e1e1e', color: '#00ff00', minHeight: '100vh' }}>
        <h1>DRONE DEMO CONTROLLER</h1>
        <h2 style={{ marginBottom: '12px' }}>No active orders to simulate.</h2>
        <button
          onClick={() => triggerRaw('at_dest_charging')}
          style={btnStyle(true)}
        >
          Startup: Arrive at Charging Base
        </button>
      </div>
    );
  }

  const returnLegPhases = ['to_charging', 'to_charging_from_restaurant', 'to_charging_from_customer'];
  const resumableReturnLegPhases = ['to_charging_from_restaurant', 'to_charging_from_customer'];
  const hasActiveTransitLeg = order.status === 'in_transit' && ['to_restaurant', 'to_customer'].includes(order.transit_phase || '');
  const hasInTransitReturnLeg = order.status === 'in_transit' && returnLegPhases.includes(order.transit_phase || '');
  const hasFailureReturnLeg = ['failed', 'stuck'].includes(order.status) && returnLegPhases.includes(order.transit_phase || '');
  const canRouteToStation = ['failed', 'stuck'].includes(order.status) && !returnLegPhases.includes(order.transit_phase || '');
  const canResumeDelivery = ['failed', 'stuck', 'in_transit'].includes(order.status) && resumableReturnLegPhases.includes(order.transit_phase || '');
  const canReturnToCharging = hasActiveTransitLeg || hasInTransitReturnLeg || order.status === 'delivered' || hasFailureReturnLeg;

  return (
    <div style={{ padding: '20px', fontFamily: 'monospace', maxWidth: '800px', background: '#1e1e1e', color: '#00ff00', minHeight: '100vh' }}>
      <h1>DRONE DEMO CONTROLLER</h1>
      <div style={{ border: '1px solid #00ff00', padding: '15px', marginBottom: '20px' }}>
        <p>ACTIVE ORDER ID: {order.id}</p>
        <p>SYSTEM PHASE: <strong>{order.status.toUpperCase()}</strong></p>
        <p>TRANSIT LEG: <strong>{(order.transit_phase || 'none').toUpperCase()}</strong></p>
      </div>

      <h2>MANUAL TRIGGERS</h2>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>

        <button
          onClick={() => trigger('at_dest_pickup')}
          disabled={!(order.status === 'in_transit' && order.transit_phase === 'to_restaurant')}
          style={btnStyle(order.status === 'in_transit' && order.transit_phase === 'to_restaurant')}
        >
          Arrive at Restaurant
        </button>

        <button
          onClick={() => trigger('at_dest_delivery')}
          disabled={!(order.status === 'in_transit' && order.transit_phase === 'to_customer')}
          style={btnStyle(order.status === 'in_transit' && order.transit_phase === 'to_customer')}
        >
          Arrive at Customer Drop-off
        </button>

        <button
          onClick={() => trigger('low_battery')}
          disabled={!hasActiveTransitLeg}
          style={btnStyle(hasActiveTransitLeg)}
        >
          Low Battery
        </button>

        <button
          onClick={() => trigger('cancel')}
          disabled={order.status !== 'arrived'}
          style={btnStyle(order.status === 'arrived')}
        >
          Cancel / Timeout
        </button>

        <button
          onClick={() => trigger('package_stuck')}
          disabled={!(order.status === 'delivering')}
          style={btnStyle(order.status === 'arrived' || order.status === 'delivering')}
        >
          Package Stuck
        </button>

        <button
          onClick={() => trigger('routed_to_station')}
          disabled={!canRouteToStation}
          style={btnStyle(canRouteToStation)}
        >
          Routed To Station
        </button>

        <button
          onClick={() => trigger('at_dest_charging')}
          disabled={!canReturnToCharging}
          style={btnStyle(canReturnToCharging)}
        >
          Return to Charging Base
        </button>

        <button
          onClick={() => trigger('resume_delivery')}
          disabled={!canResumeDelivery}
          style={btnStyle(canResumeDelivery)}
        >
          Resume Delivery After Charge
        </button>

      </div>
    </div>
  );
}

const btnStyle = (active: boolean) => ({
  background: active ? '#00ff00' : '#333',
  color: active ? '#000' : '#666',
  padding: '15px',
  border: 'none',
  fontSize: '16px',
  cursor: active ? 'pointer' : 'not-allowed',
  fontWeight: 'bold'
});

export default App;