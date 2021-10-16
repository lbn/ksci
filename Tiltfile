allow_k8s_contexts("default")
default_registry("10.42.0.1:5000")

docker_build("larcher/kscipy", "kscipy", dockerfile="infra/docker/kscipy.dockerfile")
docker_build(
    "larcher/ksci-frontend",
    "ksci-frontend",
    dockerfile="infra/docker/ksci-frontend.dockerfile",
)
docker_build(
    "larcher/ksci-consumer",
    "ksci-consumer",
    dockerfile="infra/docker/ksci-consumer.dockerfile",
)

k8s_yaml(listdir("infra/k8s"))
k8s_resource("ksci-api")
k8s_resource("ksci-worker")
k8s_resource("ksci-logwriter")
k8s_resource("ksci-statuschange")
k8s_resource("ksci-frontend")
