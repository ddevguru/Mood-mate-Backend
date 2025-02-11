import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense
from tensorflow.keras.preprocessing.image import ImageDataGenerator
import numpy as np
import cv2
import os
import json

# Load dataset
train_data_gen = ImageDataGenerator(rescale=1./255, validation_split=0.2)
train_generator = train_data_gen.flow_from_directory(
    'dataset/',
    target_size=(48, 48),
    batch_size=32,
    class_mode='categorical',
    subset='training'
)
val_generator = train_data_gen.flow_from_directory(
    'dataset/',
    target_size=(48, 48),
    batch_size=32,
    class_mode='categorical',
    subset='validation'
)

# Model
model = Sequential([
    Conv2D(32, (3,3), activation='relu', input_shape=(48, 48, 3)),
    MaxPooling2D(2,2),
    Conv2D(64, (3,3), activation='relu'),
    MaxPooling2D(2,2),
    Flatten(),
    Dense(128, activation='relu'),
    Dense(7, activation='softmax')
])

# Compile
model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

# Train
model.fit(train_generator, validation_data=val_generator, epochs=10)

# Save model
model.save('mood_model.h5')
