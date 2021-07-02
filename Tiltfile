default_registry('k3d-registry.localhost:5000')

docker_build('larcher/ksci', '.', only=['ksci', 'requirements.txt'], dockerfile='infra/docker/ksci.dockerfile')
docker_build('larcher/ksci-frontend', '.', only=['ksci-frontend', 'infra/docker/nginx'], dockerfile='infra/docker/ksci-frontend.dockerfile')

k8s_yaml(listdir('infra/k8s'))
k8s_resource('ksci-api')
k8s_resource('ksci-worker')
k8s_resource('ksci-frontend')
