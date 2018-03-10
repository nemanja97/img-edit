#! py3
# ColorEdit.py - A multiprocessing batch image editing utensil that allows you to edit one range of colors for another

import multiprocessing
from multiprocessing import Queue, Process
from time import time
from PIL import Image, ImageColor
from sys import argv
from os import listdir
from os.path import splitext, join


def print_usage():
    print('''# USAGE:
# -----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# ColorEdit.py -corecount -I -imagePath -colorName1 -colorName2                     | ColorEdit.py -corecount -D -dirPath -extension -colorName1 -colorName2
# ColorEdit.py -corecount -I -imagePath -colorName1 -colorName2 -tolerance          | ColorEdit.py -corecount -D -dirPath -extension -colorName1 -colorName2 -tolerance
# -------------------------------------------------------------------------------------------------------------------------------------------------
# ColorEdit.py -corecount -D -dirPath -extension -colorName1 -colorName2            | ColorEdit.py -corecount -D -dirPath -extension -colorRange1 -colorRange2
# ColorEdit.py -corecount -D -dirPath -extension -colorName1 -colorName2 -tolerance | ColorEdit.py -corecount -D -dirPath -extension -colorRange1 -colorRange2 -tolerance
# ---EXAMPLES------------------------------------------------------------------------------------------------------------------------------------------------------------
# python ColorEdit.py 4 I "D:\image.jpg" skyblue red 60
# python ColorEdit.py 4 I "D:\image.jpg" 255,255,0,0 red
# python ColorEdit.py 2 I "D:\image.jpg" 0,0,120,0 0,255,0,255
# python ColorEdit.py 8 D "D:\dir" .png yellow red
# python ColorEdit.py 6 D "D:\dir" .jpg 0,0,120,0 red
# -----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# corecount = Number of processes the program will spawn, you should make this value anywhere from 1 up to the number of your cpu cores
# I = Denotes that a single image will be parsed
# D = Denotes that a directory with images will be parsed
# imagePath = Path to image you with to edit
# dirPath   = Path to the directory you with to edit images in
# extension = extensions of the images you wish to edit
# colorName1, colorName2   = Color to be replaced, color to replace with
# colorRange1, colorRange2 = Numeric RGBA value to be replaced with a "," in between, numeric RGBA value to replace with a "," in between
# tolerance = Numeric value for degree of tolerance, default - 70''')


def exit_error():
    print_usage()
    quit(1)


def parse_parameters():
    # This function checks the given console parameters
    try:
        core_count = int(argv[1])
        if not core_count >= 1:
            exit_error()
    except ValueError:
        exit_error()
    if argv[2] == "I" or argv[2] == "i":
        if len(argv) == 6 or len(argv) == 7:
            try:
                image_path = argv[3]
                color_1 = argv[4]
                color_2 = argv[5]
                if len(argv) == 7:
                    tolerance = int(argv[6])
                    if tolerance > 255:
                        exit_error()
                else:
                    tolerance = 70
                return image_path, color_1, color_2, tolerance, core_count
            except Exception:
                exit_error()
        else:
            exit_error()
    elif argv[2] == "D" or argv[2] == "d":
        if len(argv) == 7 or len(argv) == 8:
            try:
                dir_path = argv[3]
                extension = argv[4]
                color_1 = argv[5]
                color_2 = argv[6]
                if len(argv) == 8:
                    tolerance = int(argv[7])
                    if tolerance > 255:
                        exit_error()
                else:
                    tolerance = 70
                return dir_path, extension, color_1, color_2, tolerance, core_count
            except Exception:
                exit_error()
        else:
            exit_error()
    else:
        exit_error()


def access_img(image_path):
    # A wrapper for valid path checking
    # params: image_path - a string representation of a path
    try:
        return Image.open(image_path)
    except IOError:
        print("Image path does not exist.")
        exit(1)


def check_color(color):
    # Checks the validity of color arguments
    # params: color - a string of color name, or RGBA value
    # VALID     : red | skyblue | 200,100,45,240
    # NOT VALID : abc | trouble | 300,100,200,50
    try:
        return ImageColor.getcolor(color, 'RGBA')
    except ValueError:
        try:
            tpl = tuple(color.split(','))
            if len(tpl) != 4:
                raise ValueError
            elif int(tpl[0]) < 0 or int(tpl[1]) < 0 or int(tpl[2]) < 0 or int(tpl[3]) < 0 or\
                    int(tpl[0]) > 255 or int(tpl[1]) > 255 or int(tpl[2]) > 255 or int(tpl[3]) > 255:
                raise ValueError
            else:
                return tuple((int(tpl[0]), int(tpl[1]), int(tpl[2]), int(tpl[3])))
        except ValueError:
            print("Invalid color value for argument > %s" % color)
            exit(1)


def check_pixel(pixel, color, tolerance):
    # Checks if pixels fits inside the given color tolerance
    return pixel[0] in range(color[0] - tolerance, color[0] + tolerance) and\
           pixel[1] in range(color[1] - tolerance, color[1] + tolerance) and\
           pixel[2] in range(color[2] - tolerance, color[2] + tolerance)


def change_pixel(pixel, color1, color2):
    # Changes the pixel to the given color, preserves shading
    try:
        # TRANSPARENCY MODE
        return color2[0] + pixel[0] - color1[0], color2[1] + pixel[1] - color1[1], color2[2] + pixel[2] - color1[2], pixel[3]
    except IndexError:
        # NON-TRANSPARENCY MODE
        return color2[0] + pixel[0] - color1[0], color2[1] + pixel[1] - color1[1], color2[2] + pixel[2] - color1[2]


def change_img(img, color1, color2, tolerance, core_count):
    # Changes the image.
    # The function spawns processes equal to the number of core_count,
    # all of whom target different cropped areas of the image being worked on.
    # Upon being changed, the crops are packed up and set into a queue.
    # Afterwards they are unpacked, and pasted over, replacing non-edited areas with edited ones.

    q = Queue()
    process_list = []

    for i in range(core_count):
        p = Process(target=change_color, args=(q, i, img.crop((i * img.size[0] // core_count, 0, (i+1) * img.size[0]//core_count, img.size[1])), color1, color2, tolerance))
        process_list.append(p)

    for i in range(core_count):
        process_list[i].start()

    # A crop container will contain the following elements:
    # 0 - The number of the area
    # 1 - The edited area itself
    # Unpacked into dictionary for easier processing

    crop_dict = {}
    for i in range(core_count):
        container = q.get()
        crop_dict[container[0]] = container[1]

    for i in range(core_count):
        img.paste(crop_dict[i], (i * img.size[0] // core_count, 0, (i+1) * img.size[0] // core_count, img.size[1]))

    for i in range(core_count):
        process_list[i].join()


def change_color(q, counter, img, color1, color2, tolerance):
    # Provides change to the color of a pixel, given it fits into the criteria
    # Afterwards, zips up the counter and the changed area and puts into a queue
    for x in range(img.size[0]):
        for y in range(img.size[1]):
            pixel = img.getpixel((x, y))
            if check_pixel(pixel, color1, tolerance):
                img.putpixel((x, y), change_pixel(pixel, color1, color2))
    q.put([counter, img])


if __name__ == "__main__":
    multiprocessing.set_start_method('spawn')
    if len(argv) > 3 and (argv[2] == "I" or argv[2] == "i"):
        # SINGLE IMAGE MODE
        start_time = time()
        image_path, color_1, color_2, tolerance, core_count = parse_parameters()
        filename, file_extension = splitext(image_path)
        WorkImg = access_img(image_path).copy()
        clr1 = check_color(color_1)
        clr2 = check_color(color_2)
        change_img(WorkImg, clr1, clr2, tolerance, core_count)
        WorkImg.save(filename + "-edit" + file_extension)
        end_time = time()
        print("Done! File : " + image_path + " - edited in : " + str(end_time - start_time))
    elif len(argv) > 3 and (argv[2] == "D" or argv[2] == "d"):
        # MULTIPLE IMAGE MODE
        dir_path, extension, color_1, color_2, tolerance, core_count = parse_parameters()
        for filename in listdir(dir_path):
            if filename.endswith(extension):
                start_time = time()
                img_path = join(dir_path, filename)
                WorkImg = access_img(img_path).copy()
                clr1 = check_color(color_1)
                clr2 = check_color(color_2)
                change_img(WorkImg, clr1, clr2, tolerance, core_count)
                WorkImg.save(img_path + "-edit" + extension)
                end_time = time()
                print("Done! File : " + dir_path + "\\" + filename + " - edited in in : " + str(end_time - start_time))
    else:
        exit_error()
