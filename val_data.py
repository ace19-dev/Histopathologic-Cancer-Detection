from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import tensorflow as tf

import random


MEAN=[0.485, 0.456, 0.406]
STD=[0.229, 0.224, 0.225]

RANDOM_CROP_SIZE = 170

class Dataset(object):
    """
    Wrapper class around the new Tensorflows dataset pipeline.

    Handles loading, partitioning, and preparing training data.
    """

    def __init__(self, tfrecord_path, batch_size, height, width):
        # self.original_size = 96

        self.resize_h = height
        self.resize_w = width

        self.dataset = tf.data.TFRecordDataset(tfrecord_path,
                                          compression_type='GZIP',
                                          num_parallel_reads=batch_size * 4)
        # dataset = dataset.map(self._parse_func, num_parallel_calls=8)
        # The map transformation takes a function and applies it to every element
        # of the dataset.
        self.dataset = self.dataset.map(self.decode, num_parallel_calls=8)
        # dataset = dataset.map(self.augment, num_parallel_calls=8)
        self.dataset = self.dataset.map(self.tencrop, num_parallel_calls=8)
        self.dataset = self.dataset.map(self.normalize, num_parallel_calls=8)

        # Prefetches a batch at a time to smooth out the time taken to load input
        # files for shuffling and processing.
        self.dataset = self.dataset.prefetch(buffer_size=batch_size)
        self.dataset = self.dataset.shuffle(1000 + 3 * batch_size)

        self.dataset = self.dataset.repeat()
        self.dataset = self.dataset.batch(batch_size)


    def decode(self, serialized_example):
        """Parses an image and label from the given `serialized_example`."""
        features = tf.parse_single_example(
            serialized_example,
            # Defaults are not specified since both keys are required.
            features={
                # 'image/filename': tf.FixedLenFeature([], tf.string),
                'image/encoded': tf.FixedLenFeature([], tf.string),
                'image/label': tf.FixedLenFeature([], tf.int64),
            })

        # Convert from a scalar string tensor to a float32 tensor with shape
        image_decoded = tf.image.decode_png(features['image/encoded'], channels=3)
        image = tf.image.resize_images(image_decoded, [self.resize_h, self.resize_w])
        # image = tf.image.central_crop(image, 0.5)
        # # paddings = tf.constant([[56,56], [56,56], [0,0]])   # 224
        # # paddings = tf.constant([[89, 89], [89, 89], [0, 0]])  # 299
        # paddings = tf.constant([[24, 24], [24, 24], [0, 0]])  # 96
        # # paddings = tf.constant([[28, 28], [28, 28], [0, 0]])  # 112
        # image = tf.pad(image, paddings, "CONSTANT")

        # Convert label from a scalar uint8 tensor to an int32 scalar.
        label = tf.cast(features['image/label'], tf.int64)

        return image, label


    def augment(self, image, label):
        """Placeholder for data augmentation.
        """
        image = tf.image.central_crop(image, 0.5)
        # paddings = tf.constant([[56,56], [56,56], [0,0]])   # 224
        # paddings = tf.constant([[89, 89], [89, 89], [0, 0]])  # 299
        paddings = tf.constant([[24, 24], [24, 24], [0, 0]])  # 96
        # paddings = tf.constant([[28, 28], [28, 28], [0, 0]])  # 112
        image = tf.pad(image, paddings, "CONSTANT")
        image = tf.image.random_flip_up_down(image)
        image = tf.image.random_flip_left_right(image)
        image = tf.image.rot90(image, k=random.randint(0,4))
        image = tf.image.random_brightness(image, max_delta=0.5)
        image = tf.image.random_contrast(image, lower=0.5, upper=1.5)
        # image = tf.image.random_hue(image, max_delta=0.04)
        # image = tf.image.random_saturation(image, lower=0.7, upper=1.3)
        # image = tf.image.resize_images(image, [self.resize_h, self.resize_w])

        return image, label


    def tencrop(self, filename, image, label):
        """Placeholder for TenCrop
        horizontal flipping is used by default
        """
        images = []
        for i in range(5):
            img = tf.random_crop(image, [RANDOM_CROP_SIZE, RANDOM_CROP_SIZE, 3])
            img = tf.image.resize(img, [self.resize_h, self.resize_w])
            images.append(img)
            images.append(tf.image.flip_left_right(img))

        return filename, tf.stack(images), label


    def normalize(self, image, label):
        # """Convert `image` from [0, 255] -> [-0.5, 0.5] floats."""
        # image = tf.cast(image, tf.float32) * (1. / 255) - 0.5

        return tf.div(tf.subtract(image, MEAN), STD), label
