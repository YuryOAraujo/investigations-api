from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError
import json
import os
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class KafkaService:
  def __init__(self):
    self.bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    self.topic = os.getenv('KAFKA_TOPIC', 'investigation-events')
    self.producer: Optional[AIOKafkaProducer] = None

  async def start_producer(self):
    try:
      self.producer = AIOKafkaProducer(
        bootstrap_servers=self.bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        compression_type='gzip',
        acks='all',
      )
      await self.producer.start()
      logger.info(f'Kafka producer started successfully, connected to {self.bootstrap_servers}')
    except Exception as e:
      logger.error(f'Failed to start Kafka producer: {e}')
      self.producer = None

  async def stop_producer(self):
    if self.producer:
      try:
        await self.producer.stop()
        logger.info('Kafka producer stopped succesfully')
      except Exception as e:
        logger.error(f'Error stopping Kafka producer: {e}')

  async def publish_event(self, event_type: str, investigation_id: int, data: dict, user: dict = None):
    if not self.producer:
      logger.warning('Kafka producer not initialized, skipping event publish')
      return
    
    event = {
      'event_type': event_type,
      'investigation_id': investigation_id,
      'timestamp': datetime.utcnow().isoformat(),
      'data': data,
      'user': user if user else None
    }

    try:
      metadata = await self.producer.send_and_wait(
        self.topic,
        value=event,
        key=str(investigation_id).encode('utf-8')
      )
      logger.info(
        f'Event published: {event_type} for investigation {investigation_id}'
        f'to partition {metadata.partition} at offset {metadata.offset}'
      )
    except KafkaError as e:
      logger.error(f'Failed to publish event: {e}')
    except Exception as e:
      logger.error(f'Unexpected error publishing event: {e}')

kafka_service = KafkaService()