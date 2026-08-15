import olefile
import re

def extract_word_doc_full_text(filename):
    '''Extract text from Word .doc file with better formatting'''
    ole = olefile.OleFileIO(filename)
    
    # Read the WordDocument stream
    word_stream = ole.openstream('WordDocument').read()
    
    ole.close()
    
    # Extract text - Word stores text as UTF-16LE in the WordDocument stream
    # Look for readable text patterns
    text = []
    i = 0
    while i < len(word_stream) - 1:
        try:
            char_code = word_stream[i] | (word_stream[i+1] << 8)
            if 32 <= char_code <= 126:  # ASCII printable
                text.append(chr(char_code))
            elif char_code == 0x000D:  # Carriage return
                text.append('\n')
            elif char_code == 0x000A:  # Line feed
                pass  # Skip, we handle with CR
            elif char_code == 0x0009:  # Tab
                text.append('\t')
            elif char_code == 0x00B7:  # Middle dot (bullet)
                text.append('•')
            elif char_code == 0x2013:  # En dash
                text.append('–')
            elif char_code == 0x2014:  # Em dash
                text.append('—')
            elif char_code == 0x2019:  # Right single quote
                text.append("'")
            elif char_code == 0x201C:  # Left double quote
                text.append('"')
            elif char_code == 0x201D:  # Right double quote
                text.append('"')
            # Latvian characters
            elif char_code == 0x0101:  # ā
                text.append('ā')
            elif char_code == 0x0113:  # ē
                text.append('ē')
            elif char_code == 0x012B:  # ī
                text.append('ī')
            elif char_code == 0x016B:  # ū
                text.append('ū')
            elif char_code == 0x0100:  # Ā
                text.append('Ā')
            elif char_code == 0x0112:  # Ē
                text.append('Ē')
            elif char_code == 0x012A:  # Ī
                text.append('Ī')
            elif char_code == 0x016A:  # Ū
                text.append('Ū')
            elif char_code == 0x010D:  # č
                text.append('č')
            elif char_code == 0x010C:  # Č
                text.append('Č')
            elif char_code == 0x0117:  # ė
                text.append('ė')
            elif char_code == 0x0173:  # ų
                text.append('ų')
            elif char_code == 0x0161:  # š
                text.append('š')
            elif char_code == 0x0160:  # Š
                text.append('Š')
            elif char_code == 0x017E:  # ž
                text.append('ž')
            elif char_code == 0x017D:  # Ž
                text.append('Ž')
            elif char_code == 0x0144:  # ń (approximation)
                text.append('ņ')
            elif char_code == 0x0143:  # Ń
                text.append('Ņ')
            elif char_code == 0x0137:  # ķ
                text.append('ķ')
            elif char_code == 0x0136:  # Ķ
                text.append('Ķ')
            elif char_code == 0x013C:  # ļ
                text.append('ļ')
            elif char_code == 0x013B:  # Ļ
                text.append('Ļ')
            elif char_code == 0x0123:  # ģ
                text.append('ģ')
            elif char_code == 0x0122:  # Ģ
                text.append('Ģ')
            elif char_code == 0x0146:  # ņ
                text.append('ņ')
            elif char_code == 0x0145:  # Ņ
                text.append('Ņ')
            elif char_code == 0x0107:  # ć
                text.append('c')
            elif char_code == 0x015B:  # ś
                text.append('s')
            elif char_code == 0x017A:  # ź
                text.append('z')
            elif char_code == 0x017C:  # ż
                text.append('z')
            elif char_code == 0x0142:  # ł
                text.append('l')
            elif char_code == 0x00A0:  # Non-breaking space
                text.append(' ')
            elif char_code > 255:  # Other unicode
                try:
                    c = chr(char_code)
                    # Check if it's a valid character (not a surrogate)
                    if not (0xD800 <= char_code <= 0xDFFF):
                        text.append(c)
                except:
                    pass
            i += 2
        except:
            i += 1
    
    result = ''.join(text)
    # Clean up formatting
    result = re.sub(r'\n+', '\n', result)
    result = re.sub(r'\t', '    ', result)
    result = re.sub(r' +', ' ', result)
    result = re.sub(r'REF\s+_Ref\d+\s+\\r\s+\\h\s+\\\*\s+MERGEFORMAT', '', result)
    result = re.sub(r'REF\s+_Ref\d+\s+\\h', '', result)
    result = re.sub(r'\\\*\s+MERGEFORMAT', '', result)
    
    return result

result = extract_word_doc_full_text(r'G:\Github\LRgr_v46.doc')

# Sanitize the result to remove any surrogates
result = result.encode('utf-8', errors='ignore').decode('utf-8')

with open(r'G:\Github\extracted_text.txt', 'w', encoding='utf-8') as f:
    f.write(result)
print(f'Extracted {len(result)} characters')
print(result[:3000])
