import re
import codecs

'''
    Find in array indices of opening and closing tag
    With the provided name
    
    Return indices (start, end)
'''
def find_pair_group(arr, name_tag = 'g'):
    startPosition = -1
    endPosition = -1

    for idx, tag in enumerate(arr):
        if tag.startswith('<' + name_tag):
            startPosition = idx
        if tag.startswith('</' + name_tag):
            endPosition = idx
            break

    return startPosition, endPosition


'''
    Find all attributes in provided tag and wrap it in dictionary 
    
    Return dictionary (key = attr, value = value of attr)
'''
def inherit_attributes(tag):
    attributes_dict = {}
    attributes = re.findall(r"[a-z-A-Z0-9]*=\".*?\"", tag)
    for attribute in attributes:
        key, value = attribute.split('=')
        attributes_dict[key] = value.replace('"', '')
    return attributes_dict

def clean_attributes(tag):
    tag = re.sub(r"[a-z-A-Z0-9]*=\".*?\"", '', tag)
    return re.sub(r"\s*", '', tag)


'''
    Add attrs into provided tag
    
    Return updated tag with attrs appended
'''
def add_attributes(tag, attrs):
    tag = clean_attributes(tag)
    ind = len(tag) - 1 # before this index we need to insert attributes
    if tag[ind - 1] == '/':
        ind -= 1
    attrs_string = ''

    for attr in attrs:
        attrs_string += (' ' + attr + '="' + attrs[attr] + '"')
    return tag[:ind] + attrs_string + tag[ind:]


'''
    Remove one group (pass group_attributes to all tags inside current group)
    
    Return updated tags (but group isn't deleted, need to delete it in source of invoking)
'''
def extend_attributes(group_attributes, group_position, tags):
    start_group, end_group = group_position
    for i in range(start_group + 1, end_group):
        cur_tag = tags[i]
        if cur_tag.startswith('</'):
            continue
        cur_tag_attributes = inherit_attributes(cur_tag)

        '''
        for attr in group_attributes: # может быть заигнорить атрибут d
            if attr in cur_tag_attributes:
                if (attr == "fill-rule" or attr == "clip-path") and (group_attributes[attr] in cur_tag_attributes[attr]): # maybe delete it
                    continue
                cur_tag_attributes[attr] = cur_tag_attributes[attr] + ' ' + group_attributes[attr]
            else:
                cur_tag_attributes[attr] = group_attributes[attr]
        '''
        # Нужно поиследовать, кто там что наследует
        for attr in group_attributes:
            if attr in cur_tag_attributes:
                if attr != "transform":
                    continue
                cur_tag_attributes[attr] = cur_tag_attributes[attr] + ' ' + group_attributes[attr] # TODO: а если это будет цвет? Не получится ли фигня?
            else:
                cur_tag_attributes[attr] = group_attributes[attr]

        tags[i] = add_attributes(cur_tag, cur_tag_attributes)

    return tags


'''
    Find all tags <...> and </...> or just <.../> (self-closing tag) 
    
    Return array of tags
'''
def find_tags(content):
    tags = []

    parsed = re.findall(r"(<.*?/>)|(<.*?>)|(</.*?>)", content)
    for tagTuple in parsed:
        tags.append(tagTuple[0] or tagTuple[1] or tagTuple[2])

    return tags


'''
    Find all paths tags into content

    Return array of paths (in tag-form)
'''
def find_paths(content):
    return re.findall(r"(<path.*?/>)", content)


'''
    Find all IDs used in svg (i.e. #name)
    
    Return list with unique names
'''
def find_all_used_ids(file_path):
    with codecs.open(file_path, encoding='utf-8', errors='ignore') as f:
        content = f.read()

    ids = []
    for cur_id in re.findall(r"url\(#.*?\)", content):
        ids.append(cur_id.split('#')[1][:-1])

    ids = list(set(ids))
    return ids


'''
    Find all tags that declare the id (from the provided array of IDs)

    Return array of tags, every tag has the id from 'ids' array
'''
def find_tags_by_ids(file_path, ids):
    with codecs.open(file_path, encoding='utf-8', errors='ignore') as f:
        content = f.read()

    tags = find_tags(content)
    tags_to_append = []

    for idx, tag in enumerate(tags):
        if tag.startswith('</'):
            continue
        cur_tag_attributes = inherit_attributes(tag)
        for attr in cur_tag_attributes:
            if attr == 'id' and (cur_tag_attributes[attr] in ids):
                tag_name = tag.split(' ')[0][1:]
                tags_after_current = tags[idx:]
                start_index, end_index = find_pair_group(tags_after_current, tag_name)
                tags_to_append.extend(tags_after_current[start_index:end_index + 1])
                break

    return tags_to_append


'''
    Remove groups by passing attributes to children of current node (inherit attributes)
    Also enumerate all paths tags with data-order property, will use to arrange tags in right order
    
    Return nothing, make new file
'''
def remove_groups_and_enumerate(file_path):
    with codecs.open(file_path, encoding='utf-8', errors='ignore') as f:
        content = f.read()

    tags = find_tags(content)

    group_position = find_pair_group(tags)
    while group_position[0] != -1:
        # process one group
        group_attributes = inherit_attributes(tags[group_position[0]])
        tags = extend_attributes(group_attributes, group_position, tags)
        tags.pop(group_position[1])
        tags.pop(group_position[0])
        group_position = find_pair_group(tags)

    order = 1
    for idx, line in enumerate(tags):
        if '<path' in line:
            tags[idx] = line[:-2] + f' data-order="{order}"' + line[-2:]
            order += 1

    newContent = '\n'.join(tags)
    with open(file_path.split('.')[0] + ' (prepared).svg', 'wb') as f:
        f.write(newContent.encode('utf-8'))

    return file_path.split('.')[0] + ' (prepared).svg'


'''
    Extract data-order attribute from the path provided by argument
    
    Return: integer number of order number    
'''
def get_order_path(path):
    order_attr = re.findall(r"data-order=\"[0-9]+\"", path)[0]

    return int(re.findall(r"[0-9]+", order_attr)[0])

'''
    Sort paths in the file (provided by path file_path) via
    data-order attribute in the tag (example: <path d="..." data-order="1"/>)
    
    Return: nothing, write to the same file (file_path)
'''
def sort_paths_tags(file_path):
    with codecs.open(file_path, encoding='utf-8', errors='ignore') as f:
        content = f.read()

    tags = find_tags(content)
    idx_start = None
    idx_end = None # included
    was_path = False
    for idx, line in enumerate(tags):
        if '<path' in line:
            if (idx_start is None) or (not was_path):
                idx_start = idx
                idx_end = idx
            else:
                idx_end = idx

            was_path = True
        else:
            was_path = False

    if idx_start is None or idx_end is None:
        return

    paths = tags[idx_start : (idx_end + 1)]
    sorted_paths = sorted(paths, key=lambda path: get_order_path(path))
    sorted_tags = tags[:idx_start] + sorted_paths + tags[(idx_end + 1):]

    sorted_tags = '\n'.join(sorted_tags)
    with open(file_path, 'w') as f:
        f.writelines(sorted_tags)

def toRGB(hexa):
    if len(hexa) == 3:
        return tuple(int(hexa[i] + hexa[i], 16) for i in range(3))
    return tuple(int(hexa[i:i + 2], 16) for i in (0, 2, 4))

def remove_white_colors(file_path):
    with codecs.open(file_path, encoding='utf-8', errors='ignore') as f:
        content = f.read()

    tags = find_tags(content)
    tags_to_append = []

    for idx, tag in enumerate(tags):
        if tag.startswith('</'):
            tags_to_append.append(tag)
            continue

        cur_tag_attributes = inherit_attributes(tag)
        has_white_color = False
        for attr in cur_tag_attributes:
            if attr == 'fill':
                print(cur_tag_attributes[attr])
                print(toRGB(cur_tag_attributes[attr][1:]))
                r, g, b = toRGB(cur_tag_attributes[attr][1:])
                if (r > 240 and g > 240 and b > 240): # TODO: константы менять
                    has_white_color = True
                break

        if not has_white_color:
            tags_to_append.append(tag)

    return tags_to_append


