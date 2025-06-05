apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: nginx-1
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
  annotations:
    argocd.argoproj.io/sync-wave: "2"
spec:
  project: default
  source:
    repoURL: https://github.com/keepkipod/router.git
    targetRevision: HEAD
    path: k8s/nginx-helm
    helm:
      releaseName: nginx-1
      valueFiles:
        - values-cell-1.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: nginx
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true