from django.db import models
from django.contrib.auth.hashers import make_password
from math import radians, sin, cos, sqrt, atan2
from ML_Model.ml_model import priority_model, food_type_encoder, scaler
import pandas as pd

class Donor(models.Model):
    donor_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)  # Add unique constraint
    contact = models.CharField(max_length=100)  # Single contact per PDF
    location_lat = models.FloatField()  # GPS latitude
    location_long = models.FloatField()  # GPS longitude
    password = models.CharField(max_length=128)  # Hashed password
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.password and not self.password.startswith(('pbkdf2_sha256$', 'bcrypt$', 'argon2')):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def calculate_distance(self, other_lat, other_long):
        R = 6371.0  # Earth radius in km
        lat1, lon1 = radians(self.location_lat), radians(self.location_long)
        lat2, lon2 = radians(other_lat), radians(other_long)
        dlat, dlon = lat2 - lat1, lon2 - lon1
        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return R * c
    
class DonorAddress(models.Model):
    donor_id = models.ForeignKey(Donor, on_delete=models.CASCADE)
    address = models.TextField()  # Multiple addresses per donor

    class Meta:
        unique_together = ('donor_id', 'address')  # Prevent duplicates

class Receiver(models.Model):
    receiver_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    contact = models.CharField(max_length=100)  # Single contact per PDF
    capacity = models.IntegerField()
    location_lat = models.FloatField()  # GPS latitude
    location_long = models.FloatField()  # GPS longitude
    password = models.CharField(max_length=128)  # Hashed password
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.password and not self.password.startswith(('pbkdf2_sha256$', 'bcrypt$', 'argon2')):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def calculate_distance(self, other_lat, other_long):
        R = 6371.0  # Earth radius in km
        lat1, lon1 = radians(self.location_lat), radians(self.location_long)
        lat2, lon2 = radians(other_lat), radians(other_long)
        dlat, dlon = lat2 - lat1, lon2 - lon1
        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return R * c

class ReceiverAddress(models.Model):
    receiver_id = models.ForeignKey(Receiver, on_delete=models.CASCADE)
    address = models.TextField()  # Multiple addresses per receiver

    class Meta:
        unique_together = ('receiver_id', 'address')  # Prevent duplicates

class FoodDonation(models.Model):
    donation_id = models.AutoField(primary_key=True)
    donor_id = models.ForeignKey(Donor, on_delete=models.CASCADE)
    food_type = models.CharField(max_length=50)
    quantity = models.IntegerField()
    unit = models.CharField(max_length=20, default='kg')
    expiry_time = models.DateTimeField()
    status = models.CharField(max_length=20, default='available')
    assigned_receiver = models.ForeignKey(
        'Receiver', on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    priority_score = models.FloatField(default=0.0)  # Add this field

    def calculate_priority_ml(self, receiver_capacity, receiver_lat, receiver_long):
        from django.utils import timezone

    # Prepare feature vector
        distance = self.donor_id.calculate_distance(receiver_lat, receiver_long)
        food_type_encoded = food_type_encoder.transform([self.food_type])[0]

        X = pd.DataFrame([{
        "receiver_capacity": receiver_capacity,
        "receiver_distance": distance,
        "food_type_encoded": food_type_encoded,
        "quantity": self.quantity,
        "time_to_expiry": (self.expiry_time - timezone.now()).total_seconds() / 3600
        }])

        self.priority_score = float(priority_model.predict(X)[0])
        self.save()
        return self.priority_score



class PickupSchedule(models.Model):
    schedule_id = models.AutoField(primary_key=True)
    donation_id = models.ForeignKey(FoodDonation, on_delete=models.CASCADE)  # 1:M with FoodDonations
    receiver_id = models.ForeignKey(Receiver, on_delete=models.CASCADE)  # 1:M with Receivers
    priority_score = models.FloatField(default=0.0)  # Conditional logic
    scheduled_time = models.DateTimeField()
    pickup_status = models.CharField(max_length=20, default='pending')


    def calculate_priority(self, current_time):
        from datetime import timedelta
        time_to_expiry = (self.donation_id.expiry_time - current_time).total_seconds() / 3600
        distance = self.receiver_id.calculate_distance(self.donation_id.donor_id.location_lat, self.donation_id.donor_id.location_long)
        return (1 - min(time_to_expiry / 24, 1)) * (1 / max(distance, 1))  # Example conditional logic

class MLPredictions(models.Model):
    prediction_id = models.AutoField(primary_key=True)
    donation_id = models.ForeignKey(FoodDonation, on_delete=models.CASCADE)  # 1:1 with FoodDonations
    expiry_risk = models.FloatField(default=0.0)  # Conditional logic
    suggested_pickup_time = models.DateTimeField(null=True, blank=True)
    model_version = models.CharField(max_length=20, default='v1.0')
    predicted_at = models.DateTimeField(auto_now_add=True)
    predicted_for = models.CharField(max_length=50, null=True, blank=True)

    def calculate_expiry_risk(self, current_time):
        from datetime import timedelta
        time_left = (self.donation_id.expiry_time - current_time).total_seconds() / 3600
        if time_left < 2:
            return 0.9
        elif time_left < 6:
            return 0.5
        return 0.1