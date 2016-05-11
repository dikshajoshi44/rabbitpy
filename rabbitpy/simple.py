"""
Wrapper methods for easy access to common operations, making them both less
complex and less verbose for one off or simple use cases.

"""
from rabbitpy import amqp_queue
from rabbitpy import connection
from rabbitpy import exchange
from rabbitpy import message


class SimpleChannel(object):
    """The rabbitpy.simple.Channel class creates a context manager
    implementation for use on a single channel where the connection is
    automatically created and managed for you.

    Example:

    .. code:: python

        import rabbitpy

        with rabbitpy.SimpleChannel(url) as channel:
            queue = rabbitpy.Queue(channel, 'my-queue')

    :param str uri: The AMQP URI to connect with. For URI options, see the
        :class:`~rabbitpy.connection.Connection` class documentation.

    """
    def __init__(self, uri):
        self.connection = None
        self.channel = None
        self.uri = uri

    def __enter__(self):
        self.connection = connection.Connection(self.uri)
        self.channel = self.connection.channel()
        return self.channel

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type and exc_val:
            raise
        self.channel.close()
        self.connection.close()


def consume(uri=None, queue_name=None, no_ack=False, prefetch=None,
            priority=None):
    """Consume messages from the queue as a generator:

    .. code:: python

        for message in rabbitpy.consume('amqp://localhost/%2F', 'my_queue'):
            message.ack()

    :param str uri: AMQP connection URI
    :param str queue_name: The name of the queue to consume from
    :param bool no_ack: Do not require acknowledgements
    :param int prefetch: Set a prefetch count for the channel
    :param int priority: Set the consumer priority
    :rtype: :py:class:`Iterator`
    :raises: py:class:`ValueError`

    """
    _validate_name(queue_name, 'queue')
    with SimpleChannel(uri) as channel:
        queue = amqp_queue.Queue(channel, queue_name)
        for msg in queue.consume(no_ack, prefetch, priority):
            yield msg


def get(uri=None, queue_name=None):
    """Get a message from RabbitMQ, auto-acknowledging with RabbitMQ if one
    is returned.

    Invoke directly as ``rabbitpy.get()``

    :param str uri: AMQP URI to connect to
    :param str queue_name: The queue name to get the message from
    :rtype: py:class:`rabbitpy.message.Message` or None
    :raises: py:class:`ValueError`

    """
    _validate_name(queue_name, 'queue')
    with SimpleChannel(uri) as channel:
        queue = amqp_queue.Queue(channel, queue_name)
        return queue.get(False)


def publish(uri=None, exchange_name=None, routing_key=None,
            body=None, properties=None, confirm=False):
    """Publish a message to RabbitMQ. This should only be used for one-off
    publishing, as you will suffer a performance penalty if you use it
    repeatedly instead creating a connection and channel and publishing on that

    :param str uri: AMQP URI to connect to
    :param str exchange_name: The exchange to publish to
    :param str routing_key: The routing_key to publish with
    :param body: The message body
    :type body: str or unicode or bytes or dict or list
    :param dict properties: Dict representation of Basic.Properties
    :param bool confirm: Confirm this delivery with Publisher Confirms
    :rtype: bool or None

    """
    if exchange_name is None:
        exchange_name = ''

    with SimpleChannel(uri) as channel:
        msg = message.Message(channel, body or '', properties or dict())
        if confirm:
            channel.enable_publisher_confirms()
            return msg.publish(exchange_name, routing_key or '',
                               mandatory=True)
        else:
            msg.publish(exchange_name, routing_key or '')


def create_queue(uri=None, queue_name='', durable=True, auto_delete=False,
                 max_length=None, message_ttl=None, expires=None,
                 dead_letter_exchange=None, dead_letter_routing_key=None,
                 arguments=None):
    """Create a queue with RabbitMQ. This should only be used for one-off
    operations. If a queue name is omitted, the name will be automatically
    generated by RabbitMQ.

    :param str uri: AMQP URI to connect to
    :param str queue_name: The queue name to create
    :param durable: Indicates if the queue should survive a RabbitMQ is restart
    :type durable: bool
    :param bool auto_delete: Automatically delete when all consumers disconnect
    :param int max_length: Maximum queue length
    :param int message_ttl: Time-to-live of a message in milliseconds
    :param expires: Milliseconds until a queue is removed after becoming idle
    :type expires: int
    :param dead_letter_exchange: Dead letter exchange for rejected messages
    :type dead_letter_exchange: str
    :param dead_letter_routing_key: Routing key for dead lettered messages
    :type dead_letter_routing_key: str
    :param dict arguments: Custom arguments for the queue
    :raises: :py:class:`ValueError`
    :raises: :py:class:`rabbitpy.RemoteClosedException`

    """
    _validate_name(queue_name, 'queue')
    with SimpleChannel(uri) as channel:
        amqp_queue.Queue(channel, queue_name,
                         durable=durable,
                         auto_delete=auto_delete,
                         max_length=max_length,
                         message_ttl=message_ttl,
                         expires=expires,
                         dead_letter_exchange=dead_letter_exchange,
                         dead_letter_routing_key=dead_letter_routing_key,
                         arguments=arguments).declare()


def delete_queue(uri=None, queue_name=None):
    """Delete a queue from RabbitMQ. This should only be used for one-off
    operations.

    :param str uri: AMQP URI to connect to
    :param str queue_name: The queue name to delete
    :rtype: bool
    :raises: :py:class:`ValueError`
    :raises: :py:class:`rabbitpy.RemoteClosedException`

    """
    _validate_name(queue_name, 'queue')
    with SimpleChannel(uri) as channel:
        amqp_queue.Queue(channel, queue_name).delete()


def create_direct_exchange(uri=None, exchange_name=None, durable=True):
    """Create a direct exchange with RabbitMQ. This should only be used for
    one-off operations.

    :param str uri: AMQP URI to connect to
    :param str exchange_name: The exchange name to create
    :param bool durable: Exchange should survive server restarts
    :raises: :py:class:`ValueError`
    :raises: :py:class:`rabbitpy.RemoteClosedException`

    """
    _create_exchange(uri, exchange_name, exchange.DirectExchange, durable)


def create_fanout_exchange(uri=None, exchange_name=None, durable=True):
    """Create a fanout exchange with RabbitMQ. This should only be used for
    one-off operations.

    :param str uri: AMQP URI to connect to
    :param str exchange_name: The exchange name to create
    :param bool durable: Exchange should survive server restarts
    :raises: :py:class:`ValueError`
    :raises: :py:class:`rabbitpy.RemoteClosedException`

    """
    _create_exchange(uri, exchange_name, exchange.FanoutExchange, durable)


def create_headers_exchange(uri=None, exchange_name=None, durable=True):
    """Create a headers exchange with RabbitMQ. This should only be used for
    one-off operations.

    :param str uri: AMQP URI to connect to
    :param str exchange_name: The exchange name to create
    :param bool durable: Exchange should survive server restarts
    :raises: :py:class:`ValueError`
    :raises: :py:class:`rabbitpy.RemoteClosedException`

    """
    _create_exchange(uri, exchange_name, exchange.HeadersExchange, durable)


def create_topic_exchange(uri=None, exchange_name=None, durable=True):
    """Create an exchange from RabbitMQ. This should only be used for one-off
    operations.

    :param str uri: AMQP URI to connect to
    :param str exchange_name: The exchange name to create
    :param bool durable: Exchange should survive server restarts
    :raises: :py:class:`ValueError`
    :raises: :py:class:`rabbitpy.RemoteClosedException`

    """
    _create_exchange(uri, exchange_name, exchange.TopicExchange, durable)


def delete_exchange(uri=None, exchange_name=None):
    """Delete an exchange from RabbitMQ. This should only be used for one-off
    operations.

    :param str uri: AMQP URI to connect to
    :param str exchange_name: The exchange name to delete
    :raises: :py:class:`ValueError`
    :raises: :py:class:`rabbitpy.RemoteClosedException`

    """
    _validate_name(exchange_name, 'exchange')
    with SimpleChannel(uri) as channel:
        exchange.Exchange(channel, exchange_name).delete()


def _create_exchange(uri, exchange_name, exchange_class, durable):
    """Create an exchange from RabbitMQ. This should only be used for one-off
    operations.

    :param str uri: AMQP URI to connect to
    :param str exchange_name: The exchange name to create
    :param bool durable: Exchange should survive server restarts
    :raises: :py:class:`ValueError`
    :raises: :py:class:`rabbitpy.RemoteClosedException`

    """
    _validate_name(exchange_name, 'exchange')
    with SimpleChannel(uri) as channel:
        exchange_class(channel, exchange_name, durable=durable).declare()


def _validate_name(value, obj_type):
    """Validate the specified name is set.

    :param str value: The value to validate
    :param str obj_type: The object type for the error message if needed
    :raises: ValueError

    """
    if not value:
        raise ValueError('You must specify the {} name'.format(obj_type))
