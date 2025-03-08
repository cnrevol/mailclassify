# train_bert_core.py
import numpy as np
import torch
from torch import nn
from torch.optim import Adam
from tqdm import tqdm
from transformers import BertTokenizer, BertModel

from sklearn.metrics import classification_report


class Dataset(torch.utils.data.Dataset):
    def __init__(self, df, tokenizer, labels):
        self.labels = [labels[label] for label in df["category"]]
        self.texts = [
            tokenizer(
                text,
                padding="max_length",
                max_length=512,
                truncation=True,
                return_tensors="pt",
            )
            for text in df["text"]
        ]

    def classes(self):
        return self.labels

    def __len__(self):
        return len(self.labels)

    def get_batch_labels(self, idx):
        return np.array(self.labels[idx])

    def get_batch_texts(self, idx):
        return self.texts[idx]

    def __getitem__(self, idx):
        batch_texts = self.get_batch_texts(idx)
        batch_y = self.get_batch_labels(idx)
        return batch_texts, batch_y


class BertClassifier(nn.Module):
    def __init__(self, model_name, num_classes, dropout=0.5):
        super(BertClassifier, self).__init__()
        self.bert = BertModel.from_pretrained(model_name)
        self.dropout = nn.Dropout(dropout)
        self.linear = nn.Linear(768, num_classes)
        self.relu = nn.ReLU()

    def forward(self, input_id, mask=None):
        if mask is None:
            mask = torch.ones_like(input_id)  # Create a mask of ones if not provided

        _, pooled_output = self.bert(
            input_ids=input_id, attention_mask=mask, return_dict=False
        )
        dropout_output = self.dropout(pooled_output)
        linear_output = self.linear(dropout_output)
        final_layer = self.relu(linear_output)
        return final_layer


def train(model, train_data, val_data, learning_rate, epochs, tokenizer, labels):
    train_dataset = Dataset(train_data, tokenizer, labels)
    val_dataset = Dataset(val_data, tokenizer, labels)

    train_dataloader = torch.utils.data.DataLoader(
        train_dataset, batch_size=2, shuffle=True
    )
    val_dataloader = torch.utils.data.DataLoader(val_dataset, batch_size=2)

    use_cuda = torch.cuda.is_available()
    device = torch.device("cuda" if use_cuda else "cpu")

    criterion = nn.CrossEntropyLoss()
    optimizer = Adam(model.parameters(), lr=learning_rate)

    if use_cuda:
        model = model.cuda()
        criterion = criterion.cuda()

    for epoch_num in range(epochs):
        total_acc_train = 0
        total_loss_train = 0

        for train_input, train_label in tqdm(train_dataloader):
            train_label = train_label.to(device)
            mask = train_input["attention_mask"].to(device)
            input_id = train_input["input_ids"].squeeze(1).to(device)

            output = model(input_id, mask)
            batch_loss = criterion(output, train_label)
            total_loss_train += batch_loss.item()

            acc = (output.argmax(dim=1) == train_label).sum().item()
            total_acc_train += acc

            model.zero_grad()
            batch_loss.backward()
            optimizer.step()

        total_acc_val = 0
        total_loss_val = 0

        with torch.no_grad():
            for val_input, val_label in val_dataloader:
                val_label = val_label.to(device)
                mask = val_input["attention_mask"].to(device)
                input_id = val_input["input_ids"].squeeze(1).to(device)

                output = model(input_id, mask)
                batch_loss = criterion(output, val_label)
                total_loss_val += batch_loss.item()

                acc = (output.argmax(dim=1) == val_label).sum().item()
                total_acc_val += acc

        print(
            f"""Epochs: {epoch_num + 1} 
              | Train Loss: {total_loss_train / len(train_data): .3f} 
              | Train Accuracy: {total_acc_train / len(train_data): .3f} 
              | Val Loss: {total_loss_val / len(val_data): .3f} 
              | Val Accuracy: {total_acc_val / len(val_data): .3f}"""
        )


def evaluate(model, test_data, tokenizer, labels):
    test_dataset = Dataset(test_data, tokenizer, labels)
    test_dataloader = torch.utils.data.DataLoader(test_dataset, batch_size=2)

    use_cuda = torch.cuda.is_available()
    device = torch.device("cuda" if use_cuda else "cpu")
    device_cpu = torch.device("cpu")

    if use_cuda:
        model = model.cuda()

    total_acc_test = 0
    y_test = []
    y_pred = []
    with torch.no_grad():
        for test_input, test_label in test_dataloader:
            test_label = test_label.to(device)
            mask = test_input["attention_mask"].to(device)
            input_id = test_input["input_ids"].squeeze(1).to(device)
            output = model(input_id, mask)
            predicted_label = output.argmax(dim=1)
            acc = (predicted_label == test_label).sum().item()
            device_cpu
            total_acc_test += acc
            # TypeError: can't convert cuda:0 device type tensor to numpy. Use Tensor.cpu() to copy the tensor to host memory first.
            test_values = test_label.cpu().tolist()
            predicted_values = predicted_label.cpu().tolist()
            y_test=y_test+test_values
            y_pred=y_pred+predicted_values

    print("Test ======================================================")
    print(f"Test Accuracy: {total_acc_test / len(test_data): .3f}")
    print("Test ======================================================")
    print(classification_report(y_test, y_pred))
