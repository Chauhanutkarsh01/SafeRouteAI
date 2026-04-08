import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor
import joblib
import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image

# 1. Define CNN Architecture
class NightlightCNN(nn.Module):
    def __init__(self):
        super(NightlightCNN, self).__init__()
        # Input shape: 3 x 64 x 64
        self.conv1 = nn.Conv2d(3, 16, kernel_size=3, stride=1, padding=1)
        self.relu1 = nn.ReLU()
        self.pool1 = nn.MaxPool2d(kernel_size=2, stride=2)
        
        # Shape: 16 x 32 x 32
        self.conv2 = nn.Conv2d(16, 32, kernel_size=3, stride=1, padding=1)
        self.relu2 = nn.ReLU()
        self.pool2 = nn.MaxPool2d(kernel_size=2, stride=2)
        
        # Shape: 32 x 16 x 16
        self.fc1 = nn.Linear(32 * 16 * 16, 64)
        self.relu3 = nn.ReLU()
        self.fc2 = nn.Linear(64, 1) # Predicts RiskScore
        
    def forward(self, x):
        x = self.pool1(self.relu1(self.conv1(x)))
        x = self.pool2(self.relu2(self.conv2(x)))
        x = x.view(x.size(0), -1) # Flatten
        x = self.relu3(self.fc1(x))
        x = self.fc2(x)
        return x

# 2. Define Dataset for CNN
class HybridDataset(Dataset):
    def __init__(self, df, transform=None):
        self.df = df.reset_index(drop=True)
        self.transform = transform
        
    def __len__(self):
        return len(self.df)
    
    def __getitem__(self, idx):
        row = self.df.iloc[idx]
        img_path = row['ImagePath']
        
        try:
            if img_path and os.path.exists(img_path):
                img = Image.open(img_path).convert('RGB')
            else:
                img = Image.new('RGB', (64, 64), color='black') # Mock if missing
        except:
            img = Image.new('RGB', (64, 64), color='black')
            
        if self.transform:
            img = self.transform(img)
            
        target = torch.tensor([row['RiskScore']], dtype=torch.float32)
        return img, target

def train_hybrid_model(data_pkl, model_out_dir):
    print(f"Loading preprocessed hybrid data from {data_pkl}...")
    df = pd.read_pickle(data_pkl)
    
    print(f"Dataset shape: {df.shape}")
    
    train_df, test_df = train_test_split(df, test_size=0.2, random_state=42)
    
    # Define features
    xgb_features = ['Grid_Lat', 'Grid_Lon', 'HourOfDay', 'DayOfWeek']
    lgb_features = [
        'retail_and_recreation_percent_change_from_baseline', 
        'grocery_and_pharmacy_percent_change_from_baseline', 
        'parks_percent_change_from_baseline', 
        'transit_stations_percent_change_from_baseline', 
        'workplaces_percent_change_from_baseline', 
        'residential_percent_change_from_baseline'
    ]
    target = 'RiskScore'
    
    # ---------------- XGBoost Training ----------------
    print("Training XGBoost Regressor on Spatial-Temporal features...")
    xgb_model = XGBRegressor(n_estimators=100, max_depth=8, learning_rate=0.1, random_state=42)
    xgb_model.fit(train_df[xgb_features], train_df[target])
    
    # ---------------- LightGBM Training ----------------
    print("Training LightGBM Regressor on Mobility features...")
    lgb_model = LGBMRegressor(n_estimators=100, max_depth=8, learning_rate=0.1, random_state=42, verbose=-1)
    lgb_model.fit(train_df[lgb_features], train_df[target])
    
    # ---------------- CNN (PyTorch) Training ----------------
    print("Training CNN on Nightlight Images...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    cnn_model = NightlightCNN().to(device)
    
    transform = transforms.Compose([
        transforms.Resize((64, 64)),
        transforms.ToTensor(),
        transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
    ])
    
    # Subsample for CNN to speed up demonstration
    cnn_train_df = train_df.sample(n=min(500, len(train_df)), random_state=42)
    train_dataset = HybridDataset(cnn_train_df, transform=transform)
    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    
    criterion = nn.MSELoss()
    optimizer = optim.Adam(cnn_model.parameters(), lr=0.001)
    
    epochs = 3
    for epoch in range(epochs):
        cnn_model.train()
        running_loss = 0.0
        for imgs, targets in train_loader:
            imgs, targets = imgs.to(device), targets.to(device)
            optimizer.zero_grad()
            outputs = cnn_model(imgs)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()
            running_loss += loss.item()
        print(f"Epoch {epoch+1}/{epochs}, CNN Loss: {running_loss/len(train_loader):.4f}")
    
    # ---------------- Evaluation & Ensemble ----------------
    print("Evaluating models on test set...")
    
    # Predictions
    xgb_preds = xgb_model.predict(test_df[xgb_features])
    lgb_preds = lgb_model.predict(test_df[lgb_features])
    
    # CNN Predictions (subsample for speed, like training)
    cnn_model.eval()
    cnn_test_df = test_df.sample(n=min(500, len(test_df)), random_state=42)
    cnn_test_dataset = HybridDataset(cnn_test_df, transform=transform)
    cnn_test_loader = DataLoader(cnn_test_dataset, batch_size=64, shuffle=False)
    cnn_sub_preds = []
    with torch.no_grad():
        for imgs, _ in cnn_test_loader:
            imgs = imgs.to(device)
            outputs = cnn_model(imgs)
            cnn_sub_preds.extend(outputs.cpu().numpy().flatten())
    cnn_mean = np.mean(cnn_sub_preds) if cnn_sub_preds else 0.0
    # Fill full test set: use subsampled preds where available, mean elsewhere
    cnn_preds = np.full(len(test_df), cnn_mean)
    cnn_preds[cnn_test_df.index.map(lambda i: test_df.index.get_loc(i))] = cnn_sub_preds
    
    # Ensemble (Simple Average)
    hybrid_preds = (xgb_preds + lgb_preds + cnn_preds) / 3.0
    
    # Metrics
    print("\n--- Model Performance Results ---")
    mse_xgb, r2_xgb = mean_squared_error(test_df[target], xgb_preds), r2_score(test_df[target], xgb_preds)
    mse_lgb, r2_lgb = mean_squared_error(test_df[target], lgb_preds), r2_score(test_df[target], lgb_preds)
    mse_cnn, r2_cnn = mean_squared_error(test_df[target], cnn_preds), r2_score(test_df[target], cnn_preds)
    mse_hyb, r2_hyb = mean_squared_error(test_df[target], hybrid_preds), r2_score(test_df[target], hybrid_preds)
    
    print(f"XGBoost | MSE: {mse_xgb:.4f}, R2: {r2_xgb:.4f}")
    print(f"LightGBM| MSE: {mse_lgb:.4f}, R2: {r2_lgb:.4f}")
    print(f"PyTorch | MSE: {mse_cnn:.4f}, R2: {r2_cnn:.4f}")
    print(f"HYBRID  | MSE: {mse_hyb:.4f}, R2: {r2_hyb:.4f}")
    print("---------------------------------\n")
    
    # ---------------- Saving ----------------
    os.makedirs(model_out_dir, exist_ok=True)
    
    joblib.dump({
        'xgb': xgb_model,
        'lgb': lgb_model
    }, os.path.join(model_out_dir, 'hybrid_tabular.pkl'))
    
    torch.save(cnn_model.state_dict(), os.path.join(model_out_dir, 'hybrid_cnn.pth'))
    
    print(f"Models successfully saved to {model_out_dir}")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(current_dir, "hybrid_aggregated_data.pkl")
    model_dir = os.path.join(current_dir, "models")
    
    train_hybrid_model(data_path, model_dir)
