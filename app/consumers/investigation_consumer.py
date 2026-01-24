from aiokafka import AIOKafkaConsumer
import json
import asyncio
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def consume_investigation_events():
    '''
    Consume and process investigation events from Kafka
    
    This consumer can be used for:
    - Audit logging
    - Sending notifications
    - Updating analytics
    - Triggering workflows
    '''
    bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    topic = os.getenv('KAFKA_TOPIC', 'investigation-events')
    
    consumer = AIOKafkaConsumer(
      topic,
      bootstrap_servers=bootstrap_servers,
      value_deserializer=lambda m: json.loads(m.decode('utf-8')),
      group_id='investigation-consumer-group',
      auto_offset_reset='earliest',
      enable_auto_commit=True
    )
    
    logger.info(f"Starting consumer for topic '{topic}' on {bootstrap_servers}")
    
    await consumer.start()
    try:
        async for msg in consumer:
          event = msg.value
          logger.info(
            f"Received event: {event['event_type']} "
            f"for investigation {event['investigation_id']} "
            f"at {event['timestamp']}"
          )
          
          if event['event_type'] == 'created':
            logger.info(f"Investigation created: {event['data']['title']}")
              
          elif event['event_type'] == 'updated':
            logger.info(f"Investigation updated: {event['investigation_id']}")
              
          elif event['event_type'] == 'deleted':
            logger.info(f"Investigation deleted: {event['data']['title']}")
              
          elif event['event_type'] == 'pdf_uploaded':
            logger.info(f"PDF uploaded: {event['data']['filename']}")
              
          elif event['event_type'] == 'pdf_deleted':
            logger.info(f"PDF deleted for investigation {event['investigation_id']}")
          
          if event.get('user'):
            logger.info(f"Action performed by: {event['user'].get('username')}")
                
    finally:
      await consumer.stop()
      logger.info('Consumer stopped')

if __name__ == '__main__':
  try:
    asyncio.run(consume_investigation_events())
  except KeyboardInterrupt:
    logger.info('Consumer interrupted by user')