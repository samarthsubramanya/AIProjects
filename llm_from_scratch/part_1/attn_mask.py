import torch

def causal_mask(T: int, device = None):
    a = torch.triu(torch.ones((T,T), dtype=torch.bool, device=device), diagonal=1)
    return a.view(1,1,T,T)