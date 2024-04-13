import torch
from torch import nn
from torch import optim

import huggingface_hub
import transformers
from transformers import AutoModel, AutoTokenizer
import time

import model


def check_model_layers(base_model, finetuned_model, trace=False):
    if trace:
        print("Base Model:")
    # print(base_model_config)
    base_dict = base_model.state_dict()
    if trace:
        for layer, weights in base_dict.items():
            print(f"Layer: {layer}, Weights: {weights.size()}")

    if trace:
        print("Finetuned Model:")
    # print(base_model_config)
    finetuned_dict = finetuned_model.state_dict()
    if trace:
        for layer, weights in base_dict.items():
            print(f"Layer: {layer}, Weights: {weights.size()}")

    # compare the weights
    for layer in base_dict.keys():
        if layer in finetuned_dict:
            if trace:
                print(f"Layer: {layer}")
                print(f"Base Model: {base_dict[layer].size()}")
                print(f"Finetuned Model: {finetuned_dict[layer].size()}")
                print("\n")
        else:
            print(f"Layer: {layer} not found in finetuned model")
            return

    for layer in finetuned_dict.keys():
        if layer in base_dict:
            if trace:
                print(f"Layer: {layer}")
                print(f"Base Model: {base_dict[layer].size()}")
                print(f"Finetuned Model: {finetuned_dict[layer].size()}")
                print("\n")
        else:
            print(f"Layer: {layer} not found in base model")
            return
        
    print("Structure of both models are same")


def check_difference(base_model, finetuned_model, device):
    base_dict = base_model.state_dict()
    finetuned_dict = finetuned_model.state_dict()

    for layer in base_dict.keys():
        if "weight" not in str(layer) and "bias" not in str(layer):
            continue
        base_weights = base_dict[layer]
        finetuned_weights = finetuned_dict[layer]
        mean_diff = torch.mean(base_weights - finetuned_weights)
        print(f"Layer {layer} has mean difference of {mean_diff}")


def weight_combine(base_model, finetuned_model, device):
    """
    Combine the weights of the models into two large tensors.
    """
    base_dict = base_model.state_dict()
    finetuned_dict = finetuned_model.state_dict()

    # combine the weights to a 1D tensor
    base_weights = []
    for layer in base_dict.keys():

        if "weight" not in str(layer) and "bias" not in str(layer):
            continue

        curr_weights = base_dict[layer]
        curr_weights = curr_weights.view(-1).to(device)
        base_weights.append(curr_weights)
    base_weights = torch.cat(base_weights, dim=0).to(device)


    finetuned_weights = []
    for layer in finetuned_dict.keys():
        if "weight" not in str(layer) and "bias" not in str(layer):
            continue

        curr_weights = finetuned_dict[layer]
        if curr_weights.is_meta:
            curr_weights = torch.zeros(curr_weights.size())
        curr_weights = curr_weights.view(-1).to(device)
        finetuned_weights.append(curr_weights)
    finetuned_weights = torch.cat(finetuned_weights, dim=0).to(device)


    return base_weights, finetuned_weights


def main():

    base_model_name, finetuned_model_name = model.select_model(1)
    device = model.get_device()

    print(device)

    base_model = model.load_model(base_model_name, device)
    base_tokenizer = model.load_tokenizer(base_model_name)
    base_model_config = base_model.config

    finetuned_model = model.load_model(finetuned_model_name, device)
    finetuned_tokenizer = model.load_tokenizer(finetuned_model_name)
    finetuned_model_config = finetuned_model.config

    check_model_layers(base_model, finetuned_model)
    print("\n")

    # check_difference(base_model, finetuned_model, device)

    base_weights, finetuned_weights = weight_combine(base_model, finetuned_model, device)
    print("Amount of trainable weights: ", finetuned_weights.size())
    print("\n")

    start_time = time.time()

    new_finetuned_weights = (finetuned_weights >= base_weights).float()
    positive_percentage = torch.count_nonzero(new_finetuned_weights) / new_finetuned_weights.size(0) * 100
    print("Percentage of positive weights: ", positive_percentage)

    print("Time taken: ", time.time() - start_time)

if __name__ == "__main__":
    main()
