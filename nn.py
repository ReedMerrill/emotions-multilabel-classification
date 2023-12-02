import argparse
import datasets
import pandas
import transformers
import tensorflow as tf
import numpy

train_path="data/train.csv", dev_path="data/dev.csv"):

# use the tokenizer from DistilRoBERTa
tokenizer = transformers.AutoTokenizer.from_pretrained("distilroberta-base")

def tokenize(examples):
    """Converts the text of each example to "input_ids", a sequence of integers
    representing 1-hot vectors for each token in the text"""
    return tokenizer(examples["text"], truncation=True, max_length=64,
                     padding="max_length")


# load the CSVs into Huggingface datasets to allow use of the tokenizer
hf_dataset = datasets.load_dataset("csv", data_files={
    "train": train_path, "validation": dev_path})

# the labels are the names of all columns except the first
labels = hf_dataset["train"].column_names[1:]

def gather_labels(example):
    """Converts the label columns into a list of 0s and 1s"""
    # the float here is because F1Score requires floats
    return {"labels": [float(example[l]) for l in labels]}

# convert text and labels to format expected by model
hf_dataset = hf_dataset.map(gather_labels)
hf_dataset = hf_dataset.map(tokenize, batched=True)

# convert Huggingface datasets to Tensorflow datasets
train_dataset = hf_dataset["train"].to_tf_dataset(
    columns="input_bow",
    label_cols="labels",
    batch_size=16,
    shuffle=True)
dev_dataset = hf_dataset["validation"].to_tf_dataset(
    columns="input_bow",
    label_cols="labels",
    batch_size=16)

# define a model with a single fully connected layer
model = tf.keras.Sequential([
    tf.keras.layers.Dense(
        units=len(labels),
        input_dim=tokenizer.vocab_size,
        activation='sigmoid')])

# specify compilation hyperparameters
model.compile(
    optimizer=tf.keras.optimizers.Adam(0.001),
    loss=tf.keras.losses.binary_crossentropy,
    metrics=[tf.keras.metrics.F1Score(average="micro", threshold=0.5)])

# fit the model to the training data, monitoring F1 on the dev data
model.fit(
    train_dataset,
    epochs=10,
    validation_data=dev_dataset,
    callbacks=[
        tf.keras.callbacks.ModelCheckpoint(
            filepath=model_path,
            monitor="val_f1_score",
            mode="max",
            save_best_only=True)])