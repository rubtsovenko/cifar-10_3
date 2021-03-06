from config import FLAGS
import tensorflow as tf
from utils import conv_bn_relu, conv, max_pool, fc, dropout, flatten_3d, prob_close, residual_unit, full_preact_unit

slim = tf.contrib.slim
xavier_conv = slim.xavier_initializer_conv2d()
xavier = slim.xavier_initializer()
var_scale = slim.variance_scaling_initializer()
const_init = tf.constant_initializer(0.1)
trunc_normal = tf.truncated_normal_initializer(mean=0, stddev=0.1)
regular = slim.l2_regularizer(FLAGS.weight_decay)


def net_1(input, is_train):
    conv1 = conv(input, filter_h=5, filter_w=5, num_filters=32, stride_y=1, stride_x=1, name='conv1')
    pool1 = max_pool(conv1, filter_h=2, filter_w=2, stride_y=2, stride_x=2, name='pool1')
    conv2 = conv(pool1, 5, 5, 64, 1, 1, 'conv2')
    pool2 = max_pool(conv2, 2, 2, 2, 2, 'pool2')
    flattened = flatten_3d(pool2, name='flattening')
    fc3 = fc(flattened, out_neurons=1000, name='fc3')
    dropout3 = dropout(fc3, keep_prob=prob_close(is_train, 0.5), name='dropout3')
    fc4 = fc(dropout3, out_neurons=10, name='fc4', relu=False)

    return fc4


def net_2(input, is_train):
    net = slim.conv2d(input, 32, [5,5], stride=1, padding='VALID',
                      weights_initializer=trunc_normal,
                      biases_initializer=const_init,
                      scope='conv1')
    net = slim.max_pool2d(net, [2,2], stride=1, scope='pool1')
    net = slim.conv2d(net, 64, [5,5], padding='VALID',
                      weights_initializer=trunc_normal,
                      biases_initializer=const_init,
                      scope='conv2')
    net = slim.max_pool2d(net, [2,2], scope='pool2')
    net = slim.flatten(net)
    net = slim.fully_connected(net, 1000,
                               weights_initializer=trunc_normal,
                               biases_initializer=const_init,
                               scope='fc3')
    net = slim.dropout(net, keep_prob=prob_close(is_train, 0.5))
    net = slim.fully_connected(net, 10, activation_fn=None,
                               weights_initializer=trunc_normal,
                               biases_initializer=const_init,
                               scope='fc4')
    return net


def net_3(input, is_train):
    with slim.arg_scope([slim.conv2d, slim.fully_connected],
                        activation_fn=tf.nn.relu,
                        weights_initializer=var_scale,
                        biases_initializer=const_init):
        with slim.arg_scope([slim.conv2d], stride=1, padding='VALID'):
            net = slim.conv2d(input, 64, [5,5], scope='conv1')
            net = slim.max_pool2d(net, [3,3], stride=2, padding='VALID', scope='pool1')
            net = tf.nn.lrn(net, bias=1.0, alpha=0.001 / 9.0, beta=0.75, name='norm1')

            net = slim.conv2d(net, 64, [5,5], scope='conv2')
            net = tf.nn.lrn(net, bias=1.0, alpha=0.001 / 9.0, beta=0.75, name='norm2')
            net = slim.max_pool2d(net, [3,3], stride=2, scope='pool2', padding='SAME')

            net = slim.flatten(net)
            net = slim.fully_connected(net, 384, weights_regularizer=regular, scope='fc3')
            net = slim.dropout(net, prob_close(is_train, 0.5), scope='dropout3')
            net = slim.fully_connected(net, 192, weights_regularizer=regular, scope='fc4')
            net = slim.dropout(net, prob_close(is_train, 0.5), scope='dropout4')
            net = slim.fully_connected(net, 10, activation_fn=None, scope='fc5')
    return net


def net_4(input, is_train):
    with slim.arg_scope([slim.conv2d, slim.fully_connected],
                        activation_fn=tf.nn.relu,
                        biases_initializer=const_init,
                        weights_initializer=var_scale,
                        weights_regularizer=slim.l2_regularizer(FLAGS.weight_decay)):
        with slim.arg_scope([slim.batch_norm],
                            decay=FLAGS.decay_bn,
                            center=True,
                            scale=True,
                            is_training=is_train):
            net = slim.conv2d(input, 32, [3, 3], scope='conv1')
            net = slim.batch_norm(net, scope='bn1')
            net = slim.conv2d(net, 32, [3, 3], scope='conv2')
            net = slim.batch_norm(net, scope='bn2')
            net = slim.max_pool2d(net, [2,2])
            net = slim.dropout(net, prob_close(is_train, 0.2))

            net = slim.conv2d(net, 64, [3, 3], scope='conv3')
            net = slim.batch_norm(net, scope='bn3')
            net = slim.conv2d(net, 64, [3, 3], scope='conv4')
            net = slim.batch_norm(net, scope='bn4')
            net = slim.max_pool2d(net, [2, 2])
            net = slim.dropout(net, prob_close(is_train, 0.3))

            net = slim.conv2d(net, 128, [3, 3], scope='conv5')
            net = slim.batch_norm(net, scope='bn5')
            net = slim.conv2d(net, 128, [3, 3], scope='conv6')
            net = slim.batch_norm(net, scope='bn6')
            net = slim.max_pool2d(net, [2, 2])
            net = slim.dropout(net, prob_close(is_train, 0.4))

            net = slim.flatten(net)
            net = slim.fully_connected(net, 10, activation_fn=None, scope='fc7', weights_regularizer=None)
    return net


def resnet20(x, is_train):
    with slim.arg_scope([slim.conv2d, slim.fully_connected],
                        activation_fn=None,
                        biases_initializer=const_init,
                        weights_initializer=var_scale,
                        weights_regularizer=slim.l2_regularizer(FLAGS.weight_decay)):
        with slim.arg_scope([slim.batch_norm],
                            decay=FLAGS.decay_bn,
                            center=True,
                            scale=True,
                            is_training=is_train):
            net = conv_bn_relu(x, filters=16, kernel=3, stride=1, scope='layer_1')

            net = residual_unit(net, filters=16, scope='unit_1', change_dim=False)
            net = residual_unit(net, filters=16, scope='unit_2', change_dim=False)
            net = residual_unit(net, filters=16, scope='unit_3', change_dim=False)

            net = residual_unit(net, filters=32, scope='unit_4', change_dim=True)
            net = residual_unit(net, filters=32, scope='unit_5', change_dim=False)
            net = residual_unit(net, filters=32, scope='unit_6', change_dim=False)

            net = residual_unit(net, filters=64, scope='unit_7', change_dim=True)
            net = residual_unit(net, filters=64, scope='unit_8', change_dim=False)
            net = residual_unit(net, filters=64, scope='unit_9', change_dim=False)

            net = slim.avg_pool2d(net, [8, 8], stride=1, scope='avgpool20')
            net = slim.flatten(net)
            net = slim.fully_connected(net, 10, activation_fn=None, scope='fc20')
    return net


def resnet20_preact(x, is_train):
    with slim.arg_scope([slim.conv2d, slim.fully_connected],
                        activation_fn=None,
                        biases_initializer=const_init,
                        weights_initializer=var_scale,
                        weights_regularizer=slim.l2_regularizer(FLAGS.weight_decay)):
        with slim.arg_scope([slim.batch_norm],
                            decay=FLAGS.decay_bn,
                            center=True,
                            scale=True,
                            is_training=is_train):
            net = conv_bn_relu(x, filters=16, kernel=3, stride=1, scope='layer_1')

            net = full_preact_unit(net, filters=16, scope='unit_1', change_dim=False)
            net = full_preact_unit(net, filters=16, scope='unit_2', change_dim=False)
            net = full_preact_unit(net, filters=16, scope='unit_3', change_dim=False)

            net = full_preact_unit(net, filters=32, scope='unit_4', change_dim=True)
            net = full_preact_unit(net, filters=32, scope='unit_5', change_dim=False)
            net = full_preact_unit(net, filters=32, scope='unit_6', change_dim=False)

            net = full_preact_unit(net, filters=64, scope='unit_7', change_dim=True)
            net = full_preact_unit(net, filters=64, scope='unit_8', change_dim=False)
            net = full_preact_unit(net, filters=64, scope='unit_9', change_dim=False)

            net = slim.avg_pool2d(net, [8, 8], stride=1, scope='avgpool20')
            net = slim.flatten(net)
            net = slim.fully_connected(net, 10, activation_fn=None, scope='fc20')
    return net