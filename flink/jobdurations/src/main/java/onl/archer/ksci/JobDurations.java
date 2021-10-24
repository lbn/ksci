package onl.archer.ksci;

import java.util.Properties;

import org.apache.flink.streaming.api.datastream.DataStreamSource;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.connectors.kafka.FlinkKafkaConsumer;
import org.apache.flink.streaming.connectors.kafka.FlinkKafkaProducer;
import org.apache.flink.api.common.state.ValueState;
import org.apache.flink.api.common.state.ValueStateDescriptor;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.streaming.api.functions.KeyedProcessFunction;
import org.apache.flink.util.Collector;

public class JobDurations {
	final static String sourceTopic = "job_status";
	final static String sinkTopic = "job_durations";
	final static String kafkaConnection = "ksci-kafka-0.ksci-kafka-brokers.kafka.svc:9092";

	static class JobStatusUpdateWithTimestamp {
		public JobStatusUpdate jobStatusUpdate;
		public long timestamp;

		public JobStatusUpdateWithTimestamp(JobStatusUpdate jobStatusUpdate, long timestamp) {
			this.jobStatusUpdate = jobStatusUpdate;
			this.timestamp = timestamp;
		}
	}

	public static class JobStateFunction
			extends KeyedProcessFunction<java.nio.ByteBuffer, JobStatusUpdate, JobDuration> {

		private ValueState<JobStatusUpdateWithTimestamp> state;

		@Override
		public void open(Configuration parameters) throws Exception {
			state = getRuntimeContext()
					.getState(new ValueStateDescriptor<>("state", JobStatusUpdateWithTimestamp.class));
		}

		@Override
		public void processElement(JobStatusUpdate value, Context ctx, Collector<JobDuration> out) throws Exception {
			JobStatusUpdateWithTimestamp start = state.value();
			long eventTime = ctx.timestamp();
			if (start == null) {
				state.update(new JobStatusUpdateWithTimestamp(value, eventTime));
			} else {
				if (value.status.equals("succeeded")) {
					JobDuration jobDuration = new JobDuration();
					jobDuration.job_id = value.job_id;
					jobDuration.duration = (int) (eventTime - start.timestamp);
					out.collect(jobDuration);
				}
			}
		}
	}

	public static void main(String[] args) throws Exception {
		final StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();

		Properties properties = new Properties();
		properties.setProperty("bootstrap.servers", kafkaConnection);
		properties.setProperty("group.id", "jobdurations");

		FlinkKafkaConsumer<JobStatusUpdate> consumer = new FlinkKafkaConsumer<JobStatusUpdate>(sourceTopic,
				new JobStatusUpdateDeserializationSchema(), properties);
		FlinkKafkaProducer<JobDuration> producer = new FlinkKafkaProducer<JobDuration>(sinkTopic,
				new JobDurationKafkaSerializer(sinkTopic), properties, FlinkKafkaProducer.Semantic.EXACTLY_ONCE);

		DataStreamSource<JobStatusUpdate> ds = env.addSource(consumer);
		ds.keyBy(value -> value.job_id).process(new JobStateFunction()).addSink(producer);
		env.execute("ksci-flink-jobdurations");
	}
}
