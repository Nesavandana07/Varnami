import zipfile, os

zip_path = r'VARNAMI DATASETS/carnatic_varnam_1.1.zip'
out_dir = r'VARNAMI DATASETS/carna_ai/carna_ai/static/samples'
os.makedirs(out_dir, exist_ok=True)

if os.path.exists(zip_path):
    z = zipfile.ZipFile(zip_path)
    samples = [
        ('carnatic_varnam_1.1/Audio/223592__gopalkoduri__carnatic-varnam-by-prasanna-in-mohanam-raaga.mp3', 'mohanam_varnam.mp3'),
        ('carnatic_varnam_1.1/Audio/223578__gopalkoduri__carnatic-varnam-by-dharini-in-abhogi-raaga.mp3', 'abhogi_varnam.mp3'),
        ('carnatic_varnam_1.1/Audio/223596__gopalkoduri__carnatic-varnam-by-sreevidya-in-sahana-raaga.mp3', 'sahana_varnam.mp3')
    ]
    for src, dst in samples:
        target = os.path.join(out_dir, dst)
        if not os.path.exists(target):
            with open(target, 'wb') as f:
                f.write(z.read(src))
            print(f"Extracted {dst}")
    print("Samples ready.")
else:
    print("Zip file not found, skipping extraction.")
