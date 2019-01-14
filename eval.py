from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import tensorflow as tf

import argparse
import os
import sys
import datetime
import csv

import eval_data

from slim.nets import resnet_v2

slim = tf.contrib.slim

FLAGS = None

PCAM_EVAL_DATA_SIZE = 57458


def main(_):
    tf.logging.set_verbosity(tf.logging.INFO)

    labels = FLAGS.labels.split(',')
    num_classes = len(labels)

    X = tf.placeholder(tf.float32, [None, FLAGS.height, FLAGS.width, 3])

    logits, _ = resnet_v2.resnet_v2_101(X,
                                        num_classes=num_classes,
                                        is_training=False)

    # prediction = tf.argmax(logits, 1, name='prediction')
    prediction = tf.nn.softmax(logits)
    predicted_labels = tf.argmax(prediction, 1)

    ###############
    # Prepare data
    ###############
    filenames = tf.placeholder(tf.string, shape=[])
    tr_dataset = eval_data.Dataset(filenames,
                                   FLAGS.batch_size,
                                   FLAGS.height,
                                   FLAGS.width)
    iterator = tr_dataset.dataset.make_one_shot_iterator()
    next_batch = iterator.get_next()

    # TensorFlow session: grow memory when needed. TF, DO NOT USE ALL MY GPU MEMORY!!!
    sess_config = tf.ConfigProto(gpu_options=tf.GPUOptions(allow_growth=True))
    with tf.Session(config=sess_config) as sess:
        # sess.run(tf.local_variables_initializer())
        sess.run(tf.global_variables_initializer())

        saver = tf.train.Saver()
        if FLAGS.tf_initial_checkpoint:
            saver.restore(sess, FLAGS.checkpoint_path)
            ckpt = tf.train.get_checkpoint_state(FLAGS.checkpoint_dir)
            if ckpt and ckpt.model_checkpoint_path:
                saver.restore(sess, ckpt.model_checkpoint_path)
                # Assuming model_checkpoint_path looks something like:
                #   /my-favorite-path/imagenet_train/model.ckpt-0,
                # extract global_step from it.
                global_step = ckpt.model_checkpoint_path.split('/')[-1].split('-')[-1]
                print('Successfully loaded model from %s at step=%s.' % (
                    ckpt.model_checkpoint_path, global_step))
            else:
                print('No checkpoint file found at %s' % FLAGS.checkpoint_dir)
                return

        # Get the number of prediction steps
        batches = int(PCAM_EVAL_DATA_SIZE / FLAGS.batch_size)
        if PCAM_EVAL_DATA_SIZE % FLAGS.batch_size > 0:
            batches += 1

        ##################################################
        # prediction & make results into csv file.
        ##################################################
        start_time = datetime.datetime.now()
        print("Start prediction: {}".format(start_time))

        id2name = {i: name for i, name in enumerate(labels)}
        submission = {}

        eval_filenames = os.path.join(FLAGS.dataset_dir, 'test.record')
        sess.run(iterator.initializer, feed_dict={filenames: eval_filenames})
        count = 0;
        for i in range(batches):
            batch_xs, filename = sess.run(next_batch)
            # # Verify image
            # n_batch = batch_xs.shape[0]
            # for i in range(n_batch):
            #     img = batch_xs[i]
            #     # scipy.misc.toimage(img).show()
            #     # Or
            #     img = cv2.cvtColor(img.astype(np.uint8), cv2.COLOR_BGR2RGB)
            #     cv2.imwrite('/home/ace19/Pictures/' + str(i) + '.png', img)
            #     # cv2.imshow(str(fnames), img)
            #     cv2.waitKey(100)
            #     cv2.destroyAllWindows()

            pred = sess.run(prediction, feed_dict={X: batch_xs})
            size = len(filename)
            for n in range(size):
                submission[filename[n].decode('UTF-8')] = id2name[pred[n]]

            count += size
            tf.logging.info('Total count: #%d' % count)

        end_time = datetime.datetime.now()
        tf.logging.info('#%d Data, End prediction: %.5f' % (PCAM_EVAL_DATA_SIZE, end_time))
        tf.logging.info('prediction waste time: %.5f' % (end_time - start_time))


    ######################################
    # make submission.csv for kaggle
    ######################################
    if not os.path.exists(FLAGS.result_dir):
        os.makedirs(FLAGS.result_dir)

    fout = open(
        os.path.join(FLAGS.result_dir,
                     FLAGS.model_architecture + '-#' +
                     global_step + '.csv'),
        'w', encoding='utf-8', newline='')
    writer = csv.writer(fout)
    writer.writerow(['id', 'label'])
    for key in sorted(submission.keys()):
        writer.writerow([key, submission[key]])
    fout.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--dataset_dir',
        type=str,
        default='/home/ace19/dl_data/histopathologic_cancer_detection',
        help="""\
            Where to find the image testing data to.
            """)
    parser.add_argument(
        '--checkpoint_path',
        type=str,
        default=os.getcwd() + './models/resnet_v2.ckpt',
        help='Directory where to read training checkpoints.')
    parser.add_argument(
        '--model_architecture',
        type=str,
        default='resnet_v2_101',
        help='What model architecture to use')
    parser.add_argument(
        '--image_height',
        type=int,
        default=224,  # nasnet, mobilenet
        help='how do you want image resize height.')
    parser.add_argument(
        '--image_width',
        type=int,
        default=224,  # nasnet, mobilenet
        help='how do you want image resize width.')
    parser.add_argument(
        '--labels',
        type=str,
        # default='Black-grass,Charlock,Cleavers,Common Chickweed,Common wheat,Fat Hen,Loose Silky-bent,Maize,Scentless Mayweed,Shepherds Purse,Small-flowered Cranesbill,Sugar beet',
        default='0,1',
        help='Labels to use', )
    parser.add_argument(
        '--batch_size',
        type=int,
        default=64,
        help='How many items to predict with at once', )
    parser.add_argument(
        '--result_dir',
        type=str,
        default=os.getcwd() + '/result',
        help='Directory to write submission.csv file.')

    FLAGS, unparsed = parser.parse_known_args()
    tf.app.run(main=main, argv=[sys.argv[0]] + unparsed)