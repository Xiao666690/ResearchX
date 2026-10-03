import hashlib
import json
def split_text_into_chunks(text, chunk_size=500):
    words = text.split()
    for i in range(0, len(words), chunk_size):
        yield ' '.join(words[i:i + chunk_size])

def cal_file_md5(file_path):
    with open(file_path, 'rb') as f:
        md5 = hashlib.md5()
        while True:
            data = f.read(4096)
            if not data:
                break
            md5.update(data)
    return md5.hexdigest()
def check_and_parse_json(input_str):
    try:
        # 加载 JSON 数据
        data = json.loads(input_str)
        # print('------------------------------------')
        # print(data)
        # 如果加载后是一个列表，取出其中的第一个对象
        if isinstance(data, list):
            if len(data) > 0:
                data = data[0]
            else:
                raise ValueError("输入数据为空列表")
        
        # 检查是否包含指定的字段
        required_fields = ["Abstract", "Primary Classification", "Secondary Classification", "Research Direction Tags"]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"JSON数据缺少必要字段 '{field}'")
        
        return data
    except ValueError as e:
        print(f"输入字符串不符合JSON格式或缺少必要字段: {e}")
        return None

if __name__ == '__main__':
    file_path = '/data1/wyyzah-work/AcadeAgent/res/pdf/a-conditional-point-diffusion-refinement-paradigm-for-3d-point-cloud-completion_ICLR_2022.pdf'
    print(cal_file_md5(file_path))