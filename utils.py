# utils.py
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from mplsoccer import Pitch
import config

# ==========================================
# 1. قسم مهندس البيانات
# ==========================================
def load_and_clean_data(file_path):
    """قراءة وتنظيف البيانات"""
    df = pd.read_csv(file_path)
    return df

# ==========================================
# 2. قسم تحليل البيانات
# ==========================================
def calculate_metrics(df):
    """حساب الإحصائيات الأساسية للفريق المفلتر"""
    total_events = len(df)
    # افترضنا أن كلمة 'Pass' موجودة في عمود tag_name (تأكد من مطابقتها لبياناتك)
    total_passes = len(df[df[config.COL_EVENT_TYPE] == 'Pass'])
    total_shots = len(df[df[config.COL_EVENT_TYPE] == 'Shot'])
    
    return total_events, total_passes, total_shots

# ==========================================
# 3. قسم الرسوميات
# ==========================================
def create_pass_map(df):
    """رسم خريطة التمريرات"""
    passes = df[df[config.COL_EVENT_TYPE] == 'Pass']
    
    if passes.empty:
        return None
        
    # استخدمنا pitch_type='custom' لأن بياناتك بالمتر
    pitch = Pitch(
        pitch_type='custom', pitch_length=105, pitch_width=68,
        pitch_color="#222222", line_color="white"
    )
    fig, ax = pitch.draw(figsize=(10, 7))
    
    # رسم الأسهم
    pitch.arrows(
        passes[config.COL_X], passes[config.COL_Y],
        passes[config.COL_END_X], passes[config.COL_END_Y],
        ax=ax, color="cyan", width=2, headwidth=5, alpha=0.7
    )
    
    # رسم نقاط البداية
    pitch.scatter(
        passes[config.COL_X], passes[config.COL_Y],
        ax=ax, color="red", s=30, alpha=0.9
    )
    
    return fig

def create_heatmap(df):
    """رسم الخريطة الحرارية لأماكن تواجد اللاعبين"""
    if df.empty:
        return None
        
    pitch = Pitch(
        pitch_type='custom', pitch_length=105, pitch_width=68,
        pitch_color="#222222", line_color="white"
    )
    fig, ax = pitch.draw(figsize=(10, 7))
    
    # رسم الكثافة الحرارية
    sns.kdeplot(
        data=df, 
        x=config.COL_X, 
        y=config.COL_Y, 
        fill=True, 
        cmap="YlOrRd", 
        ax=ax,
        thresh=0.05,
        alpha=0.6
    )
    
    ax.set_title("Heatmap", color="white", fontsize=16)
    fig.patch.set_facecolor('#222222')
    
    return fig