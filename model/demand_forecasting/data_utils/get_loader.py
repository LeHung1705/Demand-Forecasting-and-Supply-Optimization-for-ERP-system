from data_utils.data_processing import Dataset_Custom
from torch.utils.data import DataLoader

def get_loader(batch_size=128):
    train_dataset = Dataset_Custom(flag='train', scale=True)
    val_dataset = Dataset_Custom(flag='val', scale=True)
    test_dataset = Dataset_Custom(flag='test', scale=True)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

    return train_loader, val_loader, test_loader
