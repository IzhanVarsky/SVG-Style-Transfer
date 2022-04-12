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
                cur_tag_attributes[attr] = cur_tag_attributes[attr] + ' ' + group_attributes[attr]
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
    
    Return nothing, make new file
'''
def remove_groups(file_path):
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

    newContent = '\n'.join(tags)
    with open(file_path.split('.')[0] + ' (removed groups).svg', 'wb') as f:
        f.write(newContent.encode('utf-8'))

    return file_path.split('.')[0] + ' (removed groups).svg'

