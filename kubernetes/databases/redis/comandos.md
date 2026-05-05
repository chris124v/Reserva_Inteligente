# Comandos

Aqui voy a dejar algunos comandos importantes para interactuar con redis y el resto

## Aplicar cambios al cluster

```powershell
kubectl apply -f kubernetes/databases/redis/ #Tanto a service como deployment

kubectl get pods -n reservainteligente
kubectl get svc -n reservainteligente

```

## Entrar a Redis
Comandos para entrar a la bd de redis

```powershell
kubectl exec -it deployment/redis -n reservainteligente -- redis-cli

```