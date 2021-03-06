'''
 Reference:  https://www.kaggle.com/robotdreams/fine-tuning-of-vgg16-3
'''

import os
import pandas as pd
import shutil

from sklearn.utils import shuffle
from sklearn.model_selection import train_test_split

import tensorflow as tf


flags = tf.app.flags
FLAGS = flags.FLAGS


flags.DEFINE_string('label_path',
                    '/home/ace19/dl_data/histopathologic_cancer_detection/train_labels.csv',
                    'Path to label')

flags.DEFINE_string('dataset_path',
                    '/home/ace19/dl_data/histopathologic_cancer_detection',
                    'Path to label')

flags.DEFINE_string('original_dataset',
                    '/home/ace19/dl_data/histopathologic_cancer_detection/original_train',
                    'Path to original dataset')


NUM_UNDERSAMPLING = 89000

DATASET_TRAIN = 'train'
DATASET_VALIDATE = 'validate'


def transfer(files, dataset_type):
    total = len(files)

    for idx, images in enumerate(files):
        if idx % 100 == 0:
            tf.logging.info('On image %d of %d', idx, total)
        src = os.path.join(FLAGS.original_dataset, images)
        dst = os.path.join(FLAGS.dataset_path, dataset_type, images)
        shutil.copyfile(src, dst)


def main(unused_argv):
    tf.logging.set_verbosity(tf.logging.INFO)

    df = pd.read_csv(FLAGS.label_path)

    # remove error image
    df = df[df['id'] != 'dd6dfed324f9fcb6f93f46f32fc800f2ec196be2']
    # remove error black image
    df = df[df['id'] != '9369c7278ec8bcc6c880d99194de09fc2bd4efbe']

    positive = df[df['label'] == 1]
    negative = df[df['label'] == 0]

    positive = shuffle(positive)
    positive = positive[0:NUM_UNDERSAMPLING]

    negative = shuffle(negative)
    negative = negative[0:NUM_UNDERSAMPLING]

    df = pd.concat([negative, positive], axis=0)
    df = shuffle(df)

    # Split data set to train and validation sets
    train, validate = train_test_split(df, test_size=0.2, stratify=df['label'])
    # Check balancing
    tf.logging.info('True positive in train data: %s' % str(len(train[train["label"] == 1])))
    tf.logging.info('True negative in train data: %s' % str(len(train[train["label"] == 0])))
    tf.logging.info('True positive in validation data: %s' % str(len(validate[validate["label"] == 1])))
    tf.logging.info('True negative in validation data: %s' % str(len(validate[validate["label"] == 0])))

    train_path = os.path.join(FLAGS.dataset_path, 'train')
    validate_path = os.path.join(FLAGS.dataset_path, 'validate')

    if not os.path.exists(train_path):
        os.makedirs(train_path)

    if not os.path.exists(validate_path):
        os.makedirs(validate_path)

    # train_positive = train[train['label'] == 1]['id'].tolist()
    # train_positive = [name + '.png' for name in train_positive]
    #
    # train_negative = train[train['label'] == 0]['id'].tolist()
    # train_negative = [name + '.png' for name in train_negative]
    #
    # validate_positive = validate[validate['label'] == 1]['id'].tolist()
    # validate_positive = [name + '.png' for name in validate_positive]
    #
    # validate_negative = validate[validate['label'] == 0]['id'].tolist()
    # validate_negative = [name + '.png' for name in validate_negative]

    train = train['id'].tolist()
    train = [name + '.png' for name in train]

    validate = validate['id'].tolist()
    validate = [name + '.png' for name in validate]

    # Move images to directory structures
    transfer(train, DATASET_TRAIN)
    transfer(validate, DATASET_VALIDATE)


if __name__ == '__main__':
    tf.app.run()
