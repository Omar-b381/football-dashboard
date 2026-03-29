# ⚽ Football Analytics Dashboard

## 📌 تعليمات التشغيل
1. تثبيت المكتبات:
   `pip install -r requirements.txt`
2. تشغيل التطبيق:
   `streamlit run app.py`

## ⚠️ قواعد العمل للفريق
- ممنوع كتابة أي أوامر تخص `streamlit` داخل `utils.py`.
- جميع الرسوميات يجب أن تستقبل `DataFrame` وترجع `Figure`.
- الاعتماد الكلي على أسماء الأعمدة من ملف `config.py` فقط.