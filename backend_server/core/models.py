from django.db import models

class Restaurant(models.Model):
    name = models.CharField(max_length=100)

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('ready', 'Ready for Drone'),
        ('loaded', 'Loaded into Drone'),
        ('in_transit', 'In Transit'),
        ('arrived', 'Arrived at Location'),
        ('delivering', 'Lowering Food'),
        ('delivered', 'Delivered Successfully'),
        ('stuck', 'Package Stuck'),
        ('failed', 'Delivery Failed')
    ]

    TRANSIT_PHASE_CHOICES = [
        ('', 'None'),
        ('to_restaurant', 'To Restaurant'),
        ('to_customer', 'To Customer'),
        ('to_charging', 'To Charging Station'),
        ('to_charging_from_restaurant', 'To Charging Station'),
        ('to_charging_from_customer', 'To Charging Station'),
    ]

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    customer_name = models.CharField(max_length=100)
    landing_lat = models.FloatField()
    landing_lng = models.FloatField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    transit_phase = models.CharField(max_length=40, choices=TRANSIT_PHASE_CHOICES, default='', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)