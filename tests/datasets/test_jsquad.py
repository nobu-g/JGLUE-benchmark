from typing import Any

from datasets import Dataset as HFDataset
from datasets import load_dataset
from transformers import PreTrainedTokenizerBase

from datamodule.datasets.jsquad import JsquadDataset


def test_init(tokenizer: PreTrainedTokenizerBase):
    _ = JsquadDataset("train", tokenizer, max_seq_length=128, limit_examples=3)


def test_raw_examples():
    dataset: HFDataset = load_dataset("shunk031/JGLUE", name="JSQuAD", split="validation")
    for example in dataset:
        assert isinstance(example["id"], str)
        assert isinstance(example["title"], str)
        assert isinstance(example["context"], str)
        assert isinstance(example["question"], str)
        assert isinstance(example["answers"], dict)
        texts = example["answers"]["text"]
        answer_starts = example["answers"]["answer_start"]
        for text, answer_start in zip(texts, answer_starts):
            assert example["context"][answer_start:].startswith(text)
        assert example["is_impossible"] is False


def test_examples(tokenizer: PreTrainedTokenizerBase):
    dataset = JsquadDataset("validation", tokenizer, max_seq_length=128, limit_examples=10)
    for example in dataset.hf_dataset:
        for answer in example["answers"]:
            if answer["answer_start"] == -1:
                continue
            assert example["context"][answer["answer_start"] :].startswith(answer["text"])


def test_getitem(tokenizer: PreTrainedTokenizerBase):
    max_seq_length = 128
    dataset = JsquadDataset("train", tokenizer, max_seq_length, limit_examples=3)
    for i in range(len(dataset)):
        feature = dataset[i]
        assert len(feature.input_ids) == max_seq_length
        assert len(feature.attention_mask) == max_seq_length
        assert len(feature.token_type_ids) == max_seq_length
        assert isinstance(feature.start_positions, int)
        assert isinstance(feature.end_positions, int)


def test_features_0(tokenizer: PreTrainedTokenizerBase):
    max_seq_length = 128
    dataset = JsquadDataset("validation", tokenizer, max_seq_length, limit_examples=1)
    example: dict[str, Any] = dict(
        id="a10336p0q0",
        title="梅雨",
        context="梅雨 [SEP] 梅雨 （ つゆ 、 ばいう ） は 、 北海道 と 小笠原 諸島 を 除く 日本 、 朝鮮 半島 南部 、 中国 の 南部 から 長江 流域 に かけて の 沿海 部 、 および 台湾 など 、 東 アジア の 広範囲に おいて み られる 特有の 気象 現象 で 、 5 月 から 7 月 に かけて 来る 曇り や 雨 の 多い 期間 の こと 。 雨季 の 一種 である 。",
        question="日本 で 梅雨 が ない の は 北海道 と どこ か 。",
        answers=[
            dict(text="小笠原 諸島", answer_start=35),
            dict(text="小笠原 諸島 を 除く 日本", answer_start=35),
            dict(text="小笠原 諸島", answer_start=35),
        ],
        is_impossible=False,
    )
    features = dataset[0]
    question_tokens: list[str] = tokenizer.tokenize(example["question"])
    context_tokens: list[str] = tokenizer.tokenize(example["context"])
    input_tokens = (
        [tokenizer.cls_token] + question_tokens + [tokenizer.sep_token] + context_tokens + [tokenizer.sep_token]
    )
    padded_input_tokens = input_tokens + [tokenizer.pad_token] * (max_seq_length - len(input_tokens))
    assert features.input_ids == tokenizer.convert_tokens_to_ids(padded_input_tokens)
    assert features.attention_mask == [1] * len(input_tokens) + [0] * (max_seq_length - len(input_tokens))
    assert features.token_type_ids == [0] * (len(question_tokens) + 2) + [1] * (len(context_tokens) + 1) + [0] * (
        max_seq_length - len(input_tokens)
    )

    assert 0 <= features.start_positions <= features.end_positions < max_seq_length
    answer_span = slice(features.start_positions, features.end_positions + 1)
    tokenized_answer_text: str = tokenizer.decode(features.input_ids[answer_span])
    answers: list[dict[str, Any]] = example["answers"]
    assert tokenized_answer_text == answers[0]["text"]