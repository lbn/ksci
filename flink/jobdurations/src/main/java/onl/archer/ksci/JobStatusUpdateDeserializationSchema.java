package onl.archer.ksci;

import java.io.IOException;

import org.apache.flink.api.common.serialization.DeserializationSchema;
import org.apache.flink.api.common.typeinfo.TypeInformation;
import org.apache.thrift.TDeserializer;
import org.apache.thrift.TException;

public class JobStatusUpdateDeserializationSchema implements DeserializationSchema<JobStatusUpdate> {

    private static final long serialVersionUID = 1L;

    @Override
    public JobStatusUpdate deserialize(byte[] message) throws IOException {
        JobStatusUpdate event = new JobStatusUpdate();
        try {
            new TDeserializer().deserialize(event, message);
            return event;
        } catch (TException e) {
            // TODO Auto-generated catch block
            e.printStackTrace();
        }

        return event;
    }

    @Override
    public boolean isEndOfStream(JobStatusUpdate nextElement) {
        return false;
    }

    @Override
    public TypeInformation<JobStatusUpdate> getProducedType() {
        return TypeInformation.of(JobStatusUpdate.class);
    }
}