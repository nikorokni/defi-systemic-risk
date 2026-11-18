"""Persian RTL change report. Tables are read from the scored result files."""
from pathlib import Path
import html,json
import pandas as pd
from weasyprint import HTML
ROOT=Path(__file__).resolve().parents[2]
R=ROOT/"revision/results"
OUT=ROOT/"revision"


def main():
    late=pd.read_csv(R/"later_holdout/scores.csv").set_index("model")
    trans=pd.read_csv(R/"transfer/scores.csv")
    primary=pd.read_csv(R/"recomputed_metrics.csv").query("scenario == 'clean'").set_index("model")
    labels={'graph':'گراف','gru':'GRU','fixed_half':'ترکیب ثابت ۵۰/۵۰','reliability_heuristic':'ترکیب مبتنی بر اختلاف مدل‌ها','learned_gate':'گیت آموخته‌شده','freshness_capped_heuristic':'ترکیب با انقضای گراف'}
    lr=''.join(f'<tr><td>{labels[m]}</td><td dir="ltr">{r.ap:.6f}</td><td dir="ltr">{r.brier:.6f}</td><td dir="ltr">{r.logloss:.6f}</td></tr>' for m,r in late.iterrows())
    tasks=[('۱. اعتبارسنجی مستقل آن‌چین Compound','مسدود','لاگ تاریخی قرارداد با خطای ۴۰۳ رد شد؛ هیچ تطبیق موفقی ادعا نشده است.'),
      ('۲. انتقال واقعی Aave به Compound','اجراشده، مشروط','مدل‌های جدید با ویژگی مشترک آموزش یافتند؛ وزن‌ها، مقیاس‌بندی و کالیبراسیون منبع در مقصد ثابت ماندند.'),
      ('۳. بازسازی Health Factor تاریخی','تکمیل نشده','کد بازسازی حالت پایه و درخواست‌های نمونه آماده است؛ هیچ خروجی تجربی تاریخی تولید نشده است.'),
      ('۴. ارزش افزوده شبکه','بخشی اجراشده','مقایسه با ویژگی‌های محلی و بازار انجام شد؛ مقایسه کنترل‌شده با HF معتبر هنوز اجرا نشده است.'),
      ('۵. آزمون مستقل زمانی Fusion','اجراشده','۷۴۴ پیش‌بینی در بازه بعدی؛ منبع داده همان Aave است و این استقلال زمانی، استقلال منبع نیست.'),
      ('۶. آمار، جداول، نمودار و کد','بازبینی‌شده','معیارها، تفکیک فولد/نسخه، حساسیت‌ها، کالیبراسیون، صف بررسی و رخدادهای تاریخی بازتولید شدند.'),
      ('۷. بازنویسی مقاله','نسخه بازبینی علمی','نتایج منفی، فرض‌های انتقال و کارهای ناتمام صریح‌اند؛ هنوز تأیید نهایی آمادگی سابمیت ندارد.'),
      ('۸. فایل‌ها و مخزن','بسته بازتولید آماده','LaTeX، PDF، داده‌های مشتق‌شده، وزن‌های جدید، کد و گزارش تغییرات در بسته قرار دارند؛ وضعیت GitHub جدا گزارش می‌شود.')]
    tt=''.join('<tr>'+''.join('<td>'+html.escape(c)+'</td>' for c in row)+'</tr>' for row in tasks)
    integrity=json.loads((R/'integrity_audit.json').read_text())
    css='''@page {size:A4; margin:18mm 17mm; @bottom-center {content: counter(page); font-family: sans-serif; font-size:9pt; color:#607080;}}
    html {direction:rtl;} body {font-family:"Noto Naskh Arabic","DejaVu Sans",serif; font-size:11pt; line-height:1.65; color:#193146;}
    h1 {font-size:24pt;line-height:1.4;color:#12344a;margin-bottom:6mm;} h2 {font-size:15pt;color:#117c83;margin-top:7mm;break-after:avoid;} p {margin:3mm 0;}
    table {border-collapse:collapse;width:100%;margin:5mm 0;font-size:9.4pt;line-height:1.5;} th {background:#173f51;color:white;padding:3mm;text-align:right;} td {padding:2.7mm;border-bottom:1px solid #d5e0e7;vertical-align:top;} tr:nth-child(even) td {background:#f2f6f8;} tr {break-inside:avoid;}
    .lead {font-size:13pt;color:#117c83;} .note {background:#fff4df;border-right:4px solid #cf7426;padding:4mm;margin:5mm 0;} .ltr {direction:ltr;unicode-bidi:embed;font-family:"DejaVu Sans",sans-serif;font-size:9pt;}
    .small {font-size:9.5pt;color:#4b6274;} .break {break-before:page;} img {width:100%;margin:3mm 0;} a {color:#117c83;} code {direction:ltr;unicode-bidi:embed;font-family:monospace;font-size:8.5pt;}
    '''
    s=f'''<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8"><title>گزارش بازبینی پژوهش Aave</title><style>{css}</style></head><body>
    <p class="lead">گزارش تغییرات و وضعیت شواهد · ۱۷ نوامبر ۲۰۲۶</p><h1>بازبینی پژوهش هشدار زودهنگام نقدشدن وثیقه در Aave</h1>
    <p class="ltr">Early Warning of Aave Liquidation Stress under Delayed and Incomplete Network Data</p>
    <div class="note"><b>وضعیت علمی:</b> بخش عمده تحلیل و بازنویسی انجام شده است، اما اعتبارسنجی مستقل آن‌چین Compound و پنل تاریخی معتبر Health Factor هنوز تکمیل نیست. این خروجی، نسخه کاملِ بازبینی‌شده در محدوده داده‌های موجود است؛ ادعای تکمیل همه شواهد یا تضمین آمادگی/پذیرش Q1 ندارد.</div>
    <h2>وضعیت هشت درخواست</h2><table><thead><tr><th>درخواست</th><th>وضعیت</th><th>توضیح</th></tr></thead><tbody>{tt}</tbody></table>
    <h2>فایل‌های دریافت‌شده و مرز بررسی</h2><p>چهار بسته اولیه و سپس بسته کامل‌تر aave.zip بررسی شدند: نتایج اصلی، نتایج افزوده، بسته Colab، ممیزی Compound و آرشیو کامل داده Aave. شش هش داده خام در بسته جدید با اجرای قبلی یکسان است و مقادیر گراف‌های پردازش‌شده نیز مطابقت دارند. دو بارگذاری با نام‌های <span class="ltr">Aave_Research_Completed.zip</span> و <span class="ltr">Aave_Research_Completed(1).zip</span> در دسترس قرار نگرفتند و خوانده نشده‌اند. کد و آرشیوهای اصلی داده از مخزن و منابع معرفی‌شده بازیابی شد؛ این بازیابی جای ادعای خواندن فایل ناموفق را نمی‌گیرد.</p>
    <h2>صحت محاسبات و تفاوت اجراها</h2><p>تمام ۴۷ ردیف معیارهای اصلی از روی ۴۸٬۰۳۴ پیش‌بینی ضمیمه محاسبه شدند و بیشترین اختلاف حدود <span class="ltr">8.4×10⁻¹⁷</span> بود. تفکیک فولد و نسخه، حساسیت افق/هدف، کالیبراسیون، پوشش، هشدارها و پنجره‌های تاریخی نیز کنترل شدند. اختلاف اندکِ مجموع‌های دلاری در حد خطای ممیز شناور است.</p>
    <p>برچسب‌های ضمیمه و GitHub یکسان‌اند، ولی ۱۸٬۰۱۱ احتمال بیش از <span class="ltr">10⁻⁸</span> تفاوت دارند. این‌ها دو اجرای متفاوت نگه داشته شدند. بازآموزی کامل آزمایش اصلی نیز انجام شد؛ AP گراف در بازآموزی حدود ۰٫۱۹۴۹ و در ضمیمه ۰٫۱۹۵۴ است. ادعای بازتولید بیت‌به‌بیت بین نسخه‌های نرم‌افزاری متفاوت حذف شد.</p>
    <h2>نتیجه اصلی شبکه</h2><p>در ۱٬۰۲۲ پیش‌بینی و ۱۱۰ رخداد مثبت، AP مدل گراف {primary.loc['graph_platt'].ap:.4f}، GRU برابر {primary.loc['gru'].ap:.4f} و مدل مبتنی بر نقدشدن وثیقه روز قبل {primary.loc['persistence'].ap:.4f} است. اختلاف AP گراف منهای GRU برابر <span class="ltr">−0.052484</span> و بازه بوت‌استرپ ۱۴روزه <span class="ltr">[−0.148767, 0.016102]</span> است. بنابراین برتری پایدار شبکه تأیید نمی‌شود؛ این نتیجه، اثبات بی‌فایده‌بودن همه شبکه‌ها نیست.</p>
    <img src="figures/primary_performance.png"><p class="small">نمودارها از همان اجرای مبنای مقاله ساخته شده‌اند.</p>
    <h2 class="break">انتقال واقعی به Compound چه بود؟</h2><p>مدل‌های GRU و گراف با ویژگی‌های مشترک جدید ساخته شدند. آموزش با Aave در مارس تا دسامبر ۲۰۲۳ انجام شد و تنظیم/کالیبراسیون تا مارس ۲۰۲۴ ادامه داشت. سپس همان وزن‌ها و تبدیل‌های منبع روی Compound اعمال شدند. q95 تاریخی مقصد فقط برای تعریف هدف و مقیاس‌بندی تاریخی استفاده شد؛ هیچ برچسب Compound وزن منبع را آموزش نداد. مدل‌های آموزش‌دیده روی Compound، مقایسه‌گرهای مستقل‌اند.</p>
    <p>این انتقالِ مدل‌های مشترک جدید است و به‌اشتباه انتقال چک‌پوینت اصلی با تمام ویژگی‌های ذخایر نامیده نشده است. داده ناشر پنج روز حذف‌شده دارد: <span class="ltr">2024-07-05, 2024-08-01, 2024-08-05, 2024-11-25, 2024-12-20</span>. روزهای مفقود صفر نشدند و هیچ پنجره ۱۴روزه از روی آن‌ها نپرید. در نتیجه ۱۹۶ روز معتبر برای هر نسخه باقی ماند.</p>
    <table><thead><tr><th>مقصد و مدل</th><th>AP انتقال از Aave</th><th>AP آموزش روی مقصد</th></tr></thead><tbody>'''
    for v in ['c2','c3']:
        for m,label in [('shared_gru','GRU'),('shared_graph','گراف')]:
            a=trans[(trans.version==v)&(trans.model==m)&(trans.training_domain=='aave_source_only')].iloc[0]
            b=trans[(trans.version==v)&(trans.model==m)&(trans.training_domain=='compound_supervised_reference')].iloc[0]
            s+=f'<tr><td>Compound V{v[1]} / {label}</td><td dir="ltr">{a.ap:.6f}</td><td dir="ltr">{b.ap:.6f}</td></tr>'
    s+=f'''</tbody></table><p>انتقال رتبه‌بندی ضعیف است. حذف ۵ اوت، روز مهم تنش، اعتبار یک بنچمارک بحران کامل را محدود می‌کند. تطبیق عددی ستون‌های Aave در دو مجموعه، اثبات استقلال منبع یا صحت آن‌چین Compound نیست؛ مرز روز UTC و تعریف ارزش دلاری مقصد نیز هنوز مستقلاً تأیید نشده‌اند.</p>
    <h2>آزمون زمانی جدید Fusion</h2><p>پنجره جدید از ۲۵ اوت ۲۰۲۵ تا ۳۱ اوت ۲۰۲۶، شامل ۷۴۴ پیش‌بینی و ۴۰ رخداد مثبت است. گیت تنها از پیش‌بینی‌های خارج از نمونه قبلی آموزش گرفت. داده آزمون جدید برای آموزش مدل، انتخاب جریمه یا کالیبراسیون استفاده نشد. این آزمون زمانی جدید است؛ منبع داده مستقل و اجرای زنده آینده‌نگر نیست.</p>
    <table><thead><tr><th>مدل</th><th>AP</th><th>Brier</th><th>Log loss</th></tr></thead><tbody>{lr}</tbody></table>
    <p>گیت آموخته‌شده بهبود روشنی نسبت به GRU نشان نداد و Brier آن کمی بدتر شد. ترکیب ثابت AP کمی بالاتر ولی خطای احتمالاتی بیشتری داشت. گراف جدیدی بعد از اوت ۲۰۲۵ ساخته نشد؛ سن واقعی گراف از ۷ تا ۳۷۸ روز افزایش یافت. قاعده انقضای ۲۸روزه عمدتاً به مدل محلی برمی‌گردد و نزدیک‌بودن نتیجه‌اش به GRU به معنای افزودن اطلاعات شبکه نیست.</p>
    <h2>کنترل کیفیت داده جدید</h2><p>تلاش اولیه برای ادامه آزمون تا نوامبر ۲۰۲۶ به چهار قیمت منفی ETH/USD در سپتامبر برخورد کرد. قبل از هر امتیازدهیِ این آزمون، محدوده در پایان اوت متوقف و سپتامبر تا نوامبر قرنطینه شد. اصلاح طرح ثبت شده است؛ دلیل خطای منبع به‌طور حدسی تعیین نشده است.</p>
    <h2 class="break">Health Factor: انجام‌شده و انجام‌نشده</h2><p>نمونه Cred شامل ۷۵ ردیف در سال‌های ۲۰۲۱ تا ژوئن ۲۰۲۲ است و با بازه اصلی هم‌پوشانی ندارد. بازحساب فرمولِ داخل همان فایل فقط یک همانی جبری را تأیید می‌کند؛ این اعتبارسنجی تاریخی آن‌چین نیست.</p>
    <p>کد بازسازی حالت پایه با مانده توکن، بدهی، قیمت، پرچم وثیقه و قواعد عددصحیح آماده شده و موارد eMode یا ساختار ناشناخته را صریحاً رد می‌کند. ده درخواست حساب/بلوک از دوره آموزش برای بررسی مکانیک آماده است. هیچ مقدار واقعی HF برای بازه مقاله تولید نشده است. پنل تمام وام‌گیرندگان و مقایسه محلی/بازار/HF در برابر محلی/بازار/HF/شبکه همچنان اجرا نشده است.</p>
    <h2>دسترسی لازم برای بستن دو شکاف</h2><p>دسترسی عمومی، شناسه شبکه و هدر بلوک را پاسخ داد؛ اما لاگ قرارداد و وضعیت تاریخی با خطای ۴۰۳ رد شد. در این وضعیت «صفر رخداد» یا «HF سالم» گزارش نشده است. برای ادامه، یک RPC آرشیوی اتریوم با <span class="ltr">eth_call</span> تاریخی و <span class="ltr">eth_getLogs</span> و ترجیحاً منبع دوم مستقل، یا خروجی تاریخی معادل لازم است. کلید باید در تنظیم محرمانه محیط قرار گیرد؛ در مقاله، GitHub یا متن گفتگو ذخیره نمی‌شود.</p>
    <h2>تغییرات متن و ادعاها</h2><p>ساختار مقاله حول مسئله، داده/زمان‌بندی، روش، نتایج، اعتبارسنجی، بحث و محدودیت‌ها بازنویسی شد. نتایج منفی و اختلاف معیارها حفظ شدند. صد ماسک به‌عنوان صد بازآموزی معرفی نشده‌اند. آزمون زمانی و استقلال منبع تفکیک شدند. انتشار گذشته گراف و امکان دسترسی واقعی در همان تاریخ یکسان فرض نشده‌اند. ادعای پیش‌ثبت مستقل حذف شد و منابع از مستندات رسمی، مقالات و مخازن اصلی بررسی شدند.</p>
    <h2>راهنمای بسته</h2><p>PDF و LaTeX در <span class="ltr">paper/</span>، خروجی‌های جدید در <span class="ltr">revision/results/</span>، وزن‌ها در زیرپوشه‌های انتقال و آزمون بعدی، کدهای بازتولید در <span class="ltr">revision/scripts/</span> و داده‌های مشتق‌شده در <span class="ltr">revision/data/</span> قرار دارند. داده خام بزرگ از منابع اصلی با کنترل هش دریافت می‌شود. نتایج اجراهای جدا مخلوط نشده‌اند.</p>
    <p class="small">هش مبنای پیش‌بینی‌های ضمیمه:</p><p class="ltr">{integrity['ledger_sha256']}</p>
    <div class="note">هیچ نتیجه مثبت یا منبع علمی ساخته نشده است. نسخه حاضر برای بازبینی علمی مناسب‌تر شده، اما تکمیل دو بخش اعتبارسنجی و بازبینی نویسندگان پیش از ادعای آمادگی نهایی سابمیت لازم است.</div></body></html>'''
    (OUT/'CHANGELOG_FA.html').write_text(s)
    HTML(string=s,base_url=str(OUT)).write_pdf(OUT/'CHANGELOG_FA.pdf')
    print('Built Persian RTL change report',flush=True)


if __name__=='__main__':main()