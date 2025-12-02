"""
Kafka Producer with Schema Validation

Sends messages to Kafka topics with automatic Avro schema validation.
"""
import json
import logging
from typing import Dict, Optional, Any
from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient, NewTopic

logger = logging.getLogger(__name__)


class KafkaProducer:
    """
    Generic Kafka producer with schema validation
    
    Example:
        producer = KafkaProducer(
            bootstrap_servers="kafka:9092",
            topic="user_events",
            schema_path="schemas/user_event.avsc"
        )
        producer.send("user123", {"event": "login", "timestamp": 1234567890})
        producer.flush()
    """
    
    def __init__(
        self, 
        bootstrap_servers: str, 
        topic: str,
        schema_path: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Kafka producer
        
        Args:
            bootstrap_servers: Comma-separated Kafka broker addresses
            topic: Target Kafka topic
            schema_path: Path to Avro schema file for validation
            config: Additional Kafka producer configuration
        """
        self.topic = topic
        self.schema = None
        
        if schema_path:
            from data_platform.common.schemas import load_schema
            self.schema = load_schema(schema_path)
        
        producer_config = {"bootstrap.servers": bootstrap_servers}
        if config:
            producer_config.update(config)
        
        self.producer = Producer(producer_config)
        logger.info(f"Initialized Kafka producer for topic: {topic}")
    
    def send(self, key: str, value: Dict[str, Any], headers: Optional[Dict[str, str]] = None):
        """
        Validate and send message to Kafka
        
        Args:
            key: Message key (for partitioning)
            value: Message payload (dict)
            headers: Optional message headers
        """
        # Validate against schema if provided
        if self.schema:
            from data_platform.common.schemas import validate_avro
            validate_avro(value, self.schema)
        
        # Serialize value
        value_bytes = json.dumps(value).encode('utf-8')
        key_bytes = key.encode('utf-8')
        
        # Convert headers
        kafka_headers = None
        if headers:
            kafka_headers = [(k, v.encode('utf-8')) for k, v in headers.items()]
        
        # Send message
        self.producer.produce(
            topic=self.topic,
            key=key_bytes,
            value=value_bytes,
            headers=kafka_headers,
            callback=self._delivery_callback
        )
    
    def _delivery_callback(self, err, msg):
        """Callback for message delivery confirmation"""
        if err:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}] @ {msg.offset()}")
    
    def flush(self, timeout: float = 10.0):
        """
        Wait for all messages to be delivered
        
        Args:
            timeout: Maximum time to wait in seconds
        """
        remaining = self.producer.flush(timeout)
        if remaining > 0:
            logger.warning(f"{remaining} messages still in queue after flush")
    
    def close(self):
        """Close producer and clean up resources"""
        self.producer.flush()
        logger.info(f"Closed Kafka producer for topic: {self.topic}")
    
    @staticmethod
    def create_topic(bootstrap_servers: str, topic: str, num_partitions: int = 3, 
                     replication_factor: int = 1) -> bool:
        """
        Create Kafka topic if it doesn't exist
        
        Args:
            bootstrap_servers: Kafka broker addresses
            topic: Topic name to create
            num_partitions: Number of partitions
            replication_factor: Replication factor
            
        Returns:
            True if topic was created or already exists
        """
        admin_client = AdminClient({"bootstrap.servers": bootstrap_servers})
        
        topic_metadata = admin_client.list_topics(timeout=5)
        if topic in topic_metadata.topics:
            logger.info(f"Topic {topic} already exists")
            return True
        
        new_topic = NewTopic(topic, num_partitions=num_partitions, replication_factor=replication_factor)
        fs = admin_client.create_topics([new_topic])
        
        for topic_name, f in fs.items():
            try:
                f.result()
                logger.info(f"Created topic: {topic_name}")
                return True
            except Exception as e:
                logger.error(f"Failed to create topic {topic_name}: {e}")
                return False
