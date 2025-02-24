from PIL import Image
import os
import torch
from torch.utils.data import Dataset
import json
import random
import numpy as np
from transformers import CLIPTokenizer
from typing import Optional

# dataset:tokenizer, path, batch_size, minibatch_repeat, metadataを引数に取ることが必須。
# batchは"latents"か"images"のどちらかと、"captions"が必須。

class BaseDataset(Dataset):
    def __init__(
            self,
            config,
            tokenizer: CLIPTokenizer,
            path: str,
            metadata: str,
            latent: Optional[str] = "latents",
            caption: Optional[str] = "captions",
            mask: Optional[str] = None,
            pfg: Optional[str] = None,
            control: Optional[str] = None,
            prompt: Optional[str] = None,
            prefix: str = "",
            shuffle: bool = False,
            ucg: float = 0.0
        ):

        with open(os.path.join(path, metadata), "r") as f:
            self.bucket2file = json.load(f)

        self.path = path
        self.batch_size = config.train.batch_size
        self.minibatch_repeat = config.feature.minibatch_repeat
        self.minibatch_size = self.batch_size // self.minibatch_repeat
        self.tokenizer = tokenizer  # このクラスでは使っていない
        self.latent = latent
        self.caption = caption
        self.mask = mask
        self.pfg = pfg
        self.control = control
        self.prompt = prompt  # 全ての画像のcaptionをpromptにする
        self.prefix = prefix  # captionのprefix
        self.shuffle = shuffle  # バッチの取り出し方をシャッフルするかどうか（データローダー側でシャッフルした方が良い＾＾）
        self.ucg = ucg  # captionをランダムにする空文にする確率

        self.init_batch_samples()

    def __len__(self):
        return len(self.batch_samples)

    def __getitem__(self, i):
        if i == 0 and self.shuffle:
            self.init_batch_samples()

        batch = {}
        samples = self.batch_samples[i]

        latents = self.get_latents(samples, self.latent)
        batch["latents"] = torch.cat([latents]*self.minibatch_repeat, dim=0)
        captions = self.get_captions(samples, self.caption)
        batch["captions"] = captions * self.minibatch_repeat

        if self.mask:
            masks = self.get_masks(samples, self.mask if isinstance(self.mask, str) else "mask")
            batch["mask"] = torch.cat([masks]*self.minibatch_repeat, dim=0)
        if self.pfg:
            pfg = self.get_pfg(samples, self.pfg if isinstance(self.pfg, str) else "pfg")
            batch["pfg"] = torch.cat([pfg]*self.minibatch_repeat, dim=0)
        if self.control:
            control = self.get_control(samples, self.control if isinstance(self.control, str) else "control")
            batch["control"] = torch.cat([control]*self.minibatch_repeat, dim=0)

        return batch

    # バッチの取り出し方を初期化するメソッド
    def init_batch_samples(self):
        self.batch_samples = []
        for key in self.bucket2file:
            random.shuffle(self.bucket2file[key])
            self.batch_samples.extend([self.bucket2file[key][i:i+self.minibatch_size]
                                      for i in range(0, len(self.bucket2file[key]), self.minibatch_size)])
        random.shuffle(self.batch_samples)

    def get_latents(self, samples, dir="latents"):
        latents = torch.stack([torch.tensor(np.load(os.path.join(self.path, dir, sample + ".npy"))) for sample in samples])
        latents = latents.to(memory_format=torch.contiguous_format).float()  # これなに
        return latents

    def get_captions(self, samples, dir="captions"):
        captions = []
        for sample in samples:
            if self.prompt is None:
                with open(os.path.join(self.path, dir, sample + ".caption"), "r") as f:
                    caption = self.prefix + f.read()
            else:
                caption = self.prompt

            if random.random() < self.ucg:
                caption = ""
            captions.append(caption)
        return captions

    def get_masks(self, samples, dir="mask"):
        masks = torch.stack([
            torch.tensor(np.load(os.path.join(self.path, dir, sample + ".npz"))["arr_0"]).unsqueeze(0).repeat(4, 1, 1)
            for sample in samples
        ])
        masks.to(memory_format=torch.contiguous_format).float()
        return masks

    def get_pfg(self, samples, dir="pfg"):
        pfg = torch.stack([
            torch.tensor(np.load(os.path.join(self.path, dir, sample + ".npz"))["controll"]).unsqueeze(0)
            for sample in samples
        ])
        pfg.to(memory_format=torch.contiguous_format).float()
        return pfg

    def get_control(self, samples, dir="control"):
        images = []
        for sample in samples:
            image = Image.open(os.path.join(self.path, dir, sample + f".png"))
            image = np.array(image.convert("RGB"))
            image = image[None, :]
            images.append(image)
        images_tensor = np.concatenate(images, axis=0)
        images_tensor = np.array(images_tensor).astype(np.float32) / 255.0
        images_tensor = images_tensor.transpose(0, 3, 1, 2)
        images_tensor = torch.from_numpy(images_tensor).to(memory_format=torch.contiguous_format).float()
        return images_tensor
