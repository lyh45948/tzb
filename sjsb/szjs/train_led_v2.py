"""
LED 数码管 CNN 分类器训练（简洁版）
"""
import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, random_split, WeightedRandomSampler
from torchvision import datasets, transforms

DATA_ROOT = r"D:\挑战杯\11\led_digit_cls"
SAVE_DIR = r"D:\挑战杯\1\szjs\led_digit_classifier"
os.makedirs(SAVE_DIR, exist_ok=True)

transform = transforms.Compose([
    transforms.Resize((64, 64)),
    transforms.RandomRotation(degrees=8),
    transforms.ColorJitter(brightness=0.3, contrast=0.3),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]),
])

full_ds = datasets.ImageFolder(DATA_ROOT, transform=transform)
n_val = int(len(full_ds) * 0.15)
n_train = len(full_ds) - n_val
train_ds, val_ds = random_split(full_ds, [n_train, n_val], generator=torch.Generator().manual_seed(42))

# 真实样本加权（真实数据量少，需要过采样）
weights = []
for idx in train_ds.indices:
    path, _ = full_ds.samples[idx]
    if 'syn_' in os.path.basename(path):
        weights.append(1.0)
    else:
        weights.append(15.0)  # 真实样本权重15倍

sampler = WeightedRandomSampler(weights, len(weights) * 2, replacement=True)
train_loader = DataLoader(train_ds, batch_size=128, sampler=sampler, num_workers=0)
val_loader = DataLoader(val_ds, batch_size=128, shuffle=False, num_workers=0)

real_count = sum(1 for w in weights if w > 1)
print(f"Train: {n_train} (real={real_count}, syn={len(weights)-real_count}), Val: {n_val}, Classes: {full_ds.classes}")

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(128, 256, 3, padding=1), nn.BatchNorm2d(256), nn.ReLU(), nn.MaxPool2d(2),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(), nn.Linear(256*8*8, 512), nn.ReLU(), nn.Dropout(0.5), nn.Linear(512, 11)
        )
    def forward(self, x):
        return self.classifier(self.features(x))

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = Net().to(device)
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=1e-3)

best_acc = 0.0
no_improve = 0
for epoch in range(30):
    model.train()
    total_loss = correct = total = 0
    for imgs, labels in train_loader:
        imgs, labels = imgs.to(device), labels.to(device)
        optimizer.zero_grad()
        out = model(imgs)
        loss = criterion(out, labels)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * len(labels)
        correct += (out.argmax(1) == labels).sum().item()
        total += len(labels)
    train_acc = correct / total
    
    model.eval()
    correct = total = 0
    with torch.no_grad():
        for imgs, labels in val_loader:
            imgs, labels = imgs.to(device), labels.to(device)
            out = model(imgs)
            correct += (out.argmax(1) == labels).sum().item()
            total += len(labels)
    val_acc = correct / total
    
    print(f"Epoch {epoch+1:02d}: train_acc={train_acc:.4f} val_acc={val_acc:.4f}")
    
    if val_acc > best_acc:
        best_acc = val_acc
        torch.save(model.state_dict(), os.path.join(SAVE_DIR, 'best.pth'))
        print(f"  -> Saved best (val_acc={val_acc:.4f})")
        no_improve = 0
    else:
        no_improve += 1
    
    if no_improve >= 10:
        print(f"Early stopping at epoch {epoch+1}")
        break

print(f"\nBest val_acc={best_acc:.4f}")
