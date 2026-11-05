"""Remove superseded plot copies from the published folder without deleting them."""
from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[1]
backup=root/'outputs/task3_plot_backup'
for stem in ['fig1_latency_vs_rps','fig2_distributions']:
    for ext in ['pdf','png']:
        source=root/'reports/figures'/f'{stem}.{ext}'
        if source.exists():
            target=backup/source.name
            if target.exists():raise FileExistsError(target)
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.move(str(source),str(target))
ignore=root/'.gitignore'
with ignore.open('a',encoding='utf-8') as stream:
    stream.write('\n# Final submission package and local plot backups\n/task3_final_update/\n/outputs/\n')
print('Final layout applied. Previous plot copies retained locally under outputs/.')
