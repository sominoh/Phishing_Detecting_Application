import os
import random
import pandas as pd
import torch

from sklearn.model_selection import train_test_split
from torch.utils.data import Dataset, DataLoader
from transformers import BertTokenizer, BertForSequenceClassification
from torch.optim import AdamW
from tqdm import tqdm


DATASET_PATH = "ml/dataset.csv"
MODEL_SAVE_PATH = "ml/model/kobert_phishing"


replace_dict = {
    "계좌": ["통장", "금융계좌", "거래계좌", "입출금계좌"],
    "결제": ["지불", "결제 처리", "거래 승인"],
    "확인": ["검토", "점검", "검증"],
    "안내": ["통보", "고지", "공지"],
    "연락": ["통보", "문자", "전화"],
    "진행": ["처리", "수행"],
    "문의": ["질문", "질의", "요청"],
    "메시지": ["이메일", "연락", "톡"],
    "이메일": ["메시지", "문자", "톡"],
    "답변": ["회신", "응답", "안내"],
    "고객님": ["고객", "이용자", "회원"],
    "배송": ["배달", "배송 처리", "배송 진행"],
    "배송지": ["배달지", "수령지", "배송 주소"],
    "구매": ["구입", "상품 구매", "주문"],
    "주문": ["구매", "주문 접수", "상품 주문"],
    "완료": ["처리 완료", "진행 완료", "완료됨"],
    "발송": ["전송", "송부", "발송 처리"],
    "전화": ["전화통화", "연락", "유선 연락"],
    "설치": ["다운로드", "설치 진행", "프로그램 설치"],
    "내용": ["상세 내용", "관련 내용", "안내 내용"],
    "내역": ["기록", "상세 내역", "이용 내역"],

    "검사": ["주임검사"],
    "수사관": ["담당수사관", "전담수사관", "조사관"],
    "수사": ["조사", "사건조사", "수사진행"],
    "중앙지검": ["검찰청", "중앙검찰청", "지역검찰청", "지방지검", "지방검찰청"],
    "경찰청": ["국가경찰청"],
    "사이버수사대": ["사이버범죄수사대", "사이버수사팀"],
    "금융감독원": ["금감원"],

    "금융범죄": ["금융사기", "전자금융범죄", "보이스피싱범죄"],
    "대포통장": ["차명계좌", "불법계좌", "명의도용계좌"],
    "명의": ["본인명의", "명의정보", "실명정보"],
    "명의도용": ["신분도용", "개인정보도용", "계정도용"],
    "계좌추적": ["거래추적", "자금추적", "금융추적"],
    "계좌 추적": ["거래추적", "자금추적", "금융추적"],
    "불법 자금": ["범죄수익금", "의심자금", "위법자금"],
    "계좌 동결": ["거래정지", "사용정지", "계좌정지"],
    "보안 계좌": ["안전계좌", "보호계좌", "임시보호계좌"],

    "인증번호": ["OTP", "인증코드", "보안번호", "일회용코드", "비밀번호", "암호"],
    "처벌": ["형사처벌", "법적조치", "사법처리"],
    "피해": ["손해", "금전 피해", "재산 피해"],
    "보상": ["배상", "보상금", "금전 보상"],
    "소명됩니다": ["해명됩니다", "입증됩니다", "확인됩니다"],

    "통화": ["전화통화", "전화 연결", "상담"],
    "보낼게": ["첨부해 보낼게", "줄게", "보여줄게"],
    "보내줘": ["첨부해 보내줘", "줘", "보여줘"],
    "영상": ["동영상", "영상파일", "영상물"],
    "파일": ["문서", "첨부파일", "자료"],
    "돈": ["금액", "자금"],
    "사건": ["관련 사건", "해당 사건"],
    "내용": ["사항", "관련 내용"],
    "사항": ["내용", "관련 사항"],
    "고객님": ["손님", "이용자님"],
    "[Web발신]": ["[웹발신]", "[WEB발신]", "[인터넷발신]", "[Web]", "[WEB]", "[웹]"],
}


def augment_sentence(sentence, n=3):
    aug_list = []

    for _ in range(n):
        new_sentence = str(sentence)

        for k, v_list in replace_dict.items():
            if k in new_sentence and random.random() < 0.7:
                new_sentence = new_sentence.replace(k, random.choice(v_list))

        if new_sentence != sentence:
            aug_list.append(new_sentence)

    return aug_list


def load_and_augment_dataset():
    df = pd.read_csv(DATASET_PATH)

    if "구분" in df.columns:
        df = df.drop(columns=["구분"])

    if "출처" in df.columns:
        df = df.drop(columns=["출처"])

    augmented_data = []

    for _, row in df.iterrows():
        label = int(row["라벨"])
        sentence = str(row["문장"])

        base_row = row.to_dict()
        augmented_data.append(base_row)

        if label == 1:
            aug_sentences = augment_sentence(sentence, n=4)
        else:
            aug_sentences = augment_sentence(sentence, n=5)

        for s in aug_sentences:
            new_row = base_row.copy()
            new_row["문장"] = s
            augmented_data.append(new_row)

    df_aug = pd.DataFrame(augmented_data)

    df_aug = df_aug.drop_duplicates(subset=["문장"])

    texts = (
        df_aug["상황"].astype(str)
        + " "
        + df_aug["문장"].astype(str)
    ).tolist()

    labels = df_aug["라벨"].astype(int).tolist()

    return texts, labels


class ScamDataset(Dataset):
    def __init__(self, texts, labels, tokenizer):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        encoding = self.tokenizer(
            self.texts[idx],
            padding="max_length",
            truncation=True,
            max_length=128,
            return_tensors="pt"
        )

        return {
            "input_ids": encoding["input_ids"].squeeze(),
            "attention_mask": encoding["attention_mask"].squeeze(),
            "labels": torch.tensor(self.labels[idx], dtype=torch.long)
        }


def train():
    texts, labels = load_and_augment_dataset()

    train_texts, val_texts, train_labels, val_labels = train_test_split(
        texts,
        labels,
        test_size=0.1,
        random_state=42
    )

    tokenizer = BertTokenizer.from_pretrained("monologg/kobert")

    train_loader = DataLoader(
        ScamDataset(train_texts, train_labels, tokenizer),
        batch_size=4,
        shuffle=True
    )

    model = BertForSequenceClassification.from_pretrained(
        "monologg/kobert",
        num_labels=2
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model.to(device)

    optimizer = AdamW(model.parameters(), lr=2e-5)

    for epoch in range(10):
        model.train()
        total_loss = 0

        for batch in tqdm(train_loader):
            optimizer.zero_grad()

            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels_batch = batch["labels"].to(device)

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels_batch
            )

            loss = outputs.loss

            total_loss += loss.item()

            loss.backward()

            optimizer.step()

        print(f"Epoch {epoch + 1}, Loss: {total_loss}")

    os.makedirs(MODEL_SAVE_PATH, exist_ok=True)

    model.save_pretrained(MODEL_SAVE_PATH)
    tokenizer.save_pretrained(MODEL_SAVE_PATH)

    print("KoBERT 모델 저장 완료")


if __name__ == "__main__":
    train()
