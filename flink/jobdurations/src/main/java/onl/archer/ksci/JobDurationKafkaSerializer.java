package onl.archer.ksci;

import org.apache.flink.streaming.connectors.kafka.KafkaSerializationSchema;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.thrift.TException;
import org.apache.thrift.TSerializer;

public class JobDurationKafkaSerializer implements KafkaSerializationSchema<JobDuration> {
    private final String topic;

    public JobDurationKafkaSerializer(String topic) {
        super();
        this.topic = topic;
    }

    @Override
    public ProducerRecord<byte[], byte[]> serialize(JobDuration jobDuration, Long timestamp) {
        byte[] data;
        try {
            data = new TSerializer().serialize(jobDuration);
        } catch (TException e) {
            // TODO Auto-generated catch block
            e.printStackTrace();
            data = new byte[] {};
        }
        return new ProducerRecord<>(topic, data);
    }
}