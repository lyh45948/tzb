import torch
import time

print(f"GPU available: {torch.cuda.is_available()}")
device = torch.device('cuda')

duration = 3600  # 压测秒数
start = time.time()
while time.time() - start < duration:
    a = torch.randn(10000, 10000, device=device)
    b = torch.randn(10000, 10000, device=device)
    c = torch.mm(a, b)
    print(f"  GPU util: {torch.cuda.utilization()}%")

print("Done.")
