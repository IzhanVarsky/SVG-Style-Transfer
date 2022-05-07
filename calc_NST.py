from os import listdir
from gram_loss import style_loss

FOLDER = 'NST'

open('NST.txt', 'w').close()

def metric_NST():
    res = listdir(f'{FOLDER}/result')
    styles = listdir(f'{FOLDER}/style')
    for idx in range(0, len(res)):
        cur_res = f'{FOLDER}/result/{res[idx]}'
        cur_style = f'{FOLDER}/style/{styles[idx]}'
        print(cur_res, cur_style)
        loss = style_loss(result_image=cur_res, style_image=cur_style)
        with open('NST.txt', 'a') as f:
            f.write(f'{idx};{loss};\n')


metric_NST()