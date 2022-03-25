import re
import codecs

def find_pair_group(arr):
    startPosition = -1
    endPosition = -1

    for idx, tag in enumerate(arr):
        if tag.startswith('<g'):
            startPosition = idx
        if tag.startswith('</g'):
            endPosition = idx
            break

    return startPosition, endPosition

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

def add_attributes(tag, attrs):
    tag = clean_attributes(tag)
    ind = len(tag) - 1 # before this index we need to insert attributes
    if tag[ind - 1] == '/':
        ind -= 1
    attrs_string = ''

    for attr in attrs:
        attrs_string += (' ' + attr + '="' + attrs[attr] + '"')
    return tag[:ind] + attrs_string + tag[ind:]


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


with codecs.open('sample2 (1).svg', encoding='utf-8', errors='ignore') as f:
    content = f.read()

tags = []
parsed = re.findall(r"(<.*?/>)|(<.*?>)|(</.*?>)", content)
for tagTuple in parsed:
    tags.append(tagTuple[0] or tagTuple[1] or tagTuple[2])

group_position = find_pair_group(tags)
while group_position[0] != -1:
    # process one group
    group_attributes = inherit_attributes(tags[group_position[0]])
    tags = extend_attributes(group_attributes, group_position, tags)
    tags.pop(group_position[1])
    tags.pop(group_position[0])
    group_position = find_pair_group(tags)

newContent = '\n'.join(tags)
with open('sample2 (result).svg', 'wb') as f:
    f.write(newContent.encode('utf-8'))

