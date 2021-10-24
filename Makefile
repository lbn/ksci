thrift:
	rm -rf data/build && mkdir data/build
	rm -rf kscipy/data/* ksci-consumer/data/*
	docker run --user 1000:1000 -it -v ${PWD}:/workdir jaegertracing/thrift:0.14 thrift -o /workdir/data/build --gen py --gen go /workdir/data/job.thrift
	mv data/build/gen-py/ksci/* kscipy/data/
	mv data/build/gen-go/ksci/* ksci-consumer/data
docker-build:
	docker build -t larcher/ksci -f infra/docker/ksci.dockerfile ksci
	docker build -t larcher/ksci-prep -f infra/docker/ksci-prep.dockerfile ksci-finaliser
	docker build -t larcher/ksci-flink-jobdurations -f infra/docker/flink.dockerfile flink/jobdurations
