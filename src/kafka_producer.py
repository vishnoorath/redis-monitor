"""
Kafka producer for publishing DB sync changes (INSERT backlog) to Kafka topics.

Mirrors the .NET SyncChanges.KafkaProducer / GetJSOnForKafka() logic:
- Serializes each missing row as {"TableName":"...","Op":"I","Data":{...}}
- Publishes to {env}_sync_changes_backlog topic
"""

import json
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class KafkaBacklogProducer:
    """Publishes INSERT backlog rows to Kafka.

    The ``brokers`` parameter accepts either:
      - a single broker string: ``"10.10.98.39:9092"``
      - a comma-separated cluster list: ``"10.10.98.36:9092,10.10.98.37:9092,10.10.98.38:9092"``

    Both forms are passed straight through to librdkafka's ``bootstrap.servers``,
    which natively handles single and clustered topologies. ``clustered`` is just
    a hint we keep for logging / diagnostics — the client behaviour is the same.

    If broker or env is empty, all calls are no-ops (graceful fallback).
    """

    def __init__(self, broker: str, env: str, clustered: bool = False):
        # Normalize a possibly-comma-separated broker list: strip whitespace,
        # drop empty entries, re-join. confluent_kafka accepts CSV natively.
        if broker:
            brokers_clean = ','.join(
                b.strip() for b in broker.split(',') if b.strip()
            )
        else:
            brokers_clean = ''
        self._broker = brokers_clean
        self._env = env.strip().lower() if env else ''
        self._clustered = bool(clustered)
        self._producer = None

        if self._broker and self._env:
            try:
                from confluent_kafka import Producer  # noqa: F401
                self._producer = self._create_producer()
                logger.info(
                    "Kafka producer initialized: brokers=%s (%s), topic=%s",
                    self._broker,
                    'clustered' if self._clustered else 'single',
                    self.topic,
                )
            except ImportError:
                logger.warning(
                    "confluent-kafka not installed – Kafka publishing disabled. "
                    "Install with: pip install confluent-kafka"
                )
            except Exception:
                logger.exception("Failed to initialize Kafka producer")

    @property
    def topic(self) -> str:
        return f"{self._env}_sync_changes_backlog"

    @property
    def active(self) -> bool:
        return self._producer is not None

    def _create_producer(self):
        from confluent_kafka import Producer

        return Producer({
            'bootstrap.servers': self._broker,
            'client.id': 'redis-monitor-sync',
            'compression.type': 'snappy',
            'linger.ms': 10,
            'batch.size': 65536,
            # Cluster-friendly defaults. confluent-kafka connects to whichever
            # bootstrap broker answers first and discovers the rest, so single
            # and clustered topologies use the same config.
            'socket.timeout.ms': 10000,
            'message.timeout.ms': 30000,
            'retries': 5,
            'retry.backoff.ms': 200,
        })

    def publish_batch(
        self,
        table_name: str,
        column_names: List[str],
        rows: List[tuple],
    ) -> int:
        """Publish a batch of missing rows to Kafka.

        Args:
            table_name: e.g. 'Farms' (without schema)
            column_names: column names from cursor.description
            rows: list of tuples from cursor.fetchall()

        Returns:
            Number of rows successfully queued for delivery.
        """
        if not self.active or not rows:
            return 0

        published = 0
        for row in rows:
            row_dict = dict(zip(column_names, row))
            payload = self._build_payload(table_name, row_dict)

            try:
                json_bytes = json.dumps(payload, default=str).encode('utf-8')
                self._producer.produce(
                    self.topic,
                    key=row_dict.get(column_names[0]) or row_dict.get('Id') or '',
                    value=json_bytes,
                )
                # Flush periodically
                self._producer.poll(0)
                published += 1
            except Exception:
                logger.exception(
                    "Failed to produce Kafka message for table %s", table_name
                )

        # Final flush
        if published:
            self._producer.flush(timeout=5)

        logger.info(
            "Published %d/%d rows to Kafka topic '%s' for table '%s'",
            published, len(rows), self.topic, table_name,
        )
        return published

    @staticmethod
    def _build_payload(table_name: str, row_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Build the Kafka message payload (mirrors .NET GetJSOnForKafka).

        Shape:
        {
            "TableName": "[dbo].[Farms]",
            "Op": "I",
            "Data": { "FarmId": "...", "FarmName": "...", ... }
        }
        """
        data = {}
        for col, val in row_dict.items():
            data[col] = _serialize_value(val)

        return {
            "TableName": f"[dbo].[{table_name}]",
            "Op": "I",
            "Data": data,
        }


def _serialize_value(val: Any) -> Any:
    """Convert a pyodbc column value to a JSON-serializable type.

    Matches .NET GetJSOnForKafka() type handling:
    - datetime → "yyyy-MM-dd HH:mm:ss"
    - bytes/varbinary → hex string
    - bool → JSON boolean
    - None/DBNull → JSON null
    """
    if val is None:
        return None

    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d %H:%M:%S")

    if isinstance(val, date):
        return val.strftime("%Y-%m-%d")

    if isinstance(val, bytes):
        return val.hex()

    if isinstance(val, bool):
        return val

    # int, float, str pass through as-is (JSON-serializable)
    return val
