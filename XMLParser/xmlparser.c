#include <stdio.h>
#include <string.h>
#include <stdbool.h>
#include <stdlib.h> // Required for malloc
#include <ctype.h>  // Required for isspace()

#ifdef _WIN32
    #define DLL_EXPORT __declspec(dllexport)
#else
    #define DLL_EXPORT __attribute__((visibility("default")))
#endif


typedef struct DOMNode
{
    // 1. Data Fields
    char *tag;       // Stores the tag pointer (e.g., "div", "p", "h1")

    int attrcount;

    char **attrKey;   // Stores the attribute pointer (e.g., "width", "id")
    char **attrVal;   // Stores the attribute pointer (e.g., "100", "main")
    char *innerText; // Stores the text inside the tag pointer

    bool isLeaf;
    bool isRoot;

    // 2. Structural Pointers (The Linkage)
    struct DOMNode *firstChild;  // Points DOWN to the first nested element
    struct DOMNode *nextSibling; // Points SIDEWAYS to the next element at the same level
} DOMNode;



void trim_whitespace(char *str)
{
    if (str == NULL)
        return;

    int len = (int)strlen(str);
    if (len == 0)
        return;

    // 1. Find the first non-whitespace character (Leading)
    int start = 0;
    while (start < len && isspace((unsigned char)str[start]))
    {
        start++;
    }

    // 2. Find the last non-whitespace character (Trailing)
    int end = len - 1;
    while (end >= start && isspace((unsigned char)str[end]))
    {
        end--;
    }

    // 3. Shift the characters forward if there were leading spaces
    int i;
    for (i = start; i <= end; i++)
    {
        str[i - start] = str[i];
    }

    // 4. Null-terminate the brand new end of the string
    str[i - start] = '\0';
}

void copyTagPure(char tag[],int size,char * copyTo,char *paramsstring)
{
    int blankspace = 0;
    int copytosize = 0;
    int copyparamstrsize = 0;
    bool copytoparamsstr = false;
    for (int i = 0; i < size; i++)
    {
       char cont = tag[i];
       if(cont == ' ')
       {
        blankspace++;

        if(blankspace == 1)
        {
            copytoparamsstr = true;
        }

        if(copytoparamsstr==true)
        {
            *(paramsstring+copyparamstrsize)=cont;
            copyparamstrsize++;
        }
    
       }
       else
       {
        if(copytoparamsstr == true)
        {
            *(paramsstring+copyparamstrsize)=cont;
            copyparamstrsize++;
        }
        else{
        *(copyTo+copytosize) = cont;
        copytosize++;
        }
       }
    }

    copyTo[copytosize] = '\0';
    paramsstring[copyparamstrsize] = '\0';
    
}

int countsubStr(char c, char content[], int length)
{
    int counter = 0;
    for (int i = 0; i < length; i++)
    {
        if (c == content[i])
        {
            counter++;
        }
    }
    return counter;
}

char *strdup(const char *src)
{
    int len = (int)strlen(src) + 1;
    char *dst = (char *)malloc(len * sizeof(char));
    if (dst != NULL)
    {
        strcpy(dst, src);
    }
    return dst;
}

int compareRawstr(char s1[], char s2[], int length1, int length2)
{
    if (length1 != length2)
    {
        return false;
    }
    for (int i = 0; i < length1; i++)
    {
        if (s1[i] != s2[i])
        {
            return false;
        }
    }
    return true;
}

void TagParser(char paramsstring[], int size, DOMNode *node)
{
    char buffer[size + 1];
    int buffsize = 0;

    bool istagprocessed = false;
    bool isparsingParamkey = true;
    bool isparsingParamValue = false;
    bool paramskeyinit = false;
    char startchar = ' ';
    bool insidequote = false;


    char key[size][512];

    int keysize = 0;

    char value[size][2048];
    int valuesize = 0;

    for (int i = 0; i < size; i++)
    {
        char content = paramsstring[i];

        if (content == '=' && !insidequote)
        {
            // Change the operation from key to params
            isparsingParamkey = false;
            isparsingParamValue = true;
            buffer[buffsize] = '\0';

            // Put buffer into the key and clean it
            strcpy(key[keysize], buffer);
            // printf("Debug:KEY name:%s\n",key[keysize]);
            keysize++;
            buffsize = 0;
            strcpy(buffer, "");
        }
        else if (isparsingParamkey == true && isparsingParamValue == false)
        {
            // printf("Debug:Added to buffer for key:%c\n",content);
            buffer[buffsize] = content; // put value in buffer
            buffsize++;
        }
        else if (isparsingParamValue == true && isparsingParamkey == false)
        {
            if (content == '\"' || content == '\'')
            {
                if (paramskeyinit == true)
                {
                    if (startchar == content)
                    {

                        //printf("Debug:params value recording stopped...\n");
                        // stop it
                        insidequote = false;
                        isparsingParamValue = false;
                        isparsingParamkey = true;
                        paramskeyinit = false;

                        // clean buffer and add the value to key
                        buffer[buffsize] = '\0';
                        strcpy(value[valuesize], buffer);
                        strcpy(buffer, "");
                        buffsize = 0;
                        valuesize++;

                        // reset startchar to blank
                        startchar = ' ';
                    }
                    else
                    {
                        // Add it to buffer
                        buffer[buffsize] = content;
                        buffsize++;
                    }
                }
                else
                {
                    //printf("Debug:value recording started..\n");
                    insidequote = true;
                    startchar = content; // Store the current char so that we can match it in time of the closing
                    paramskeyinit = true;
                }

                continue;
            }
            else if (paramskeyinit == true)
            {
                // Else put it into buffer
                //  printf("Debug:Added to buffer for value:%c\n",content);
                buffer[buffsize] = content;
                buffsize++;
            }
        }

        // =========================================================
        // THE BRIDGE: Allocate memory directly to the node arrays
        // =========================================================
    }

    node->attrcount = keysize;

    if (keysize > 0)
    {
        // Now that fields are char**, these lines compile flawlessly
        node->attrKey = (char **)malloc(sizeof(char *) * keysize);
        node->attrVal = (char **)malloc(sizeof(char *) * keysize);

        for (int i = 0; i < keysize; i++)
        {
            node->attrKey[i] = strdup(key[i]);

            if (i < valuesize)
            {
                node->attrVal[i] = strdup(value[i]);
                //printf("DEBUG:The value is:%s\n", value[i]);
            }
            else
            {
                node->attrVal[i] = strdup("");
            }
        }
    }
    else
    {
        node->attrKey = NULL;
        node->attrVal = NULL;
    }

    // printf("KeySize:%d ValueSize:%d\n", keysize, valuesize);
}



void freeDOMTree(DOMNode *node) {
    if (node == NULL) return;

    // 1. Recursively clear branches down and sideways
    freeDOMTree(node->firstChild);
    freeDOMTree(node->nextSibling);

    // 2. Free internal attribute arrays
    for (int i = 0; i < node->attrcount; i++) {
        free(node->attrKey[i]);
        free(node->attrVal[i]);
    }
    if (node->attrcount > 0) {
        free(node->attrKey);
        free(node->attrVal);
    }

    // 3. Free text and tag strings, then the node itself
    free(node->tag);
    free(node->innerText);
    free(node);
}

void Parser(char htmlContent[], int startPointer, int depth, bool isFirst, DOMNode *upline)
{
    int ContentLength = (int)strlen(htmlContent) - startPointer;

    char *tag = (char *)malloc(sizeof(char) * (ContentLength) + 1);
    int tagpos = 0;

    char *tagpure = (char *)malloc(sizeof(char) * (ContentLength) + 1);     // store pure tag
    char *opentagpure = (char *)malloc(sizeof(char) * (ContentLength) + 1); // store pure tag in case of it is open

    char *paramstr = (char *)malloc(sizeof(char) * (ContentLength) + 1); // store param str

    char *innerHTML = (char *)malloc(sizeof(char) * (ContentLength) + 1);
    int htmlpos = 0;

    char *Endtag = (char *)malloc(sizeof(char) * (ContentLength) + 1);
    int Endtagpos = 0;

    char *Opentagtemp = (char *)malloc(sizeof(char) * (ContentLength) + 1);
    int opentagtemppos = 0;

    bool isEndslashgot = false;

    int tagStack = 0;

    int isInitTagStarted = false;
    int isInitTagEnded = false;
    int isEndTagStarted = false;
    int isEndTagEnded = false;

    char *contentprocessed = (char *)malloc(sizeof(char) * (ContentLength) + 1);
    int contentlen = 0;
    int offset = 0;
    char quotechar;

    bool isInsideQuote = false;

    for (int i = startPointer; i < (int)strlen(htmlContent); i++)
    {
        char charecter = htmlContent[i];

        if (charecter == '"' || charecter == '\'')
        {
            if(isInsideQuote)
            {
                // We need to check if the quote is correct one and then stop else ignore
                if(charecter == quotechar)
                {
                    isInsideQuote = false; // stop it
                    quotechar = ' ';
                }
                // else it will be ignored
            }
            else
            {
                // this is the starting make isIndsideQuote True and store the quote
                isInsideQuote = true;
                quotechar = charecter;
            }
        }

        if (charecter == '<' && isInsideQuote==false && isInitTagStarted == false)
        {
            isInitTagStarted = true;
        }
        else if (charecter == '>' && isInsideQuote==false && isInitTagStarted == true && isEndTagStarted == false)
        {
            tagStack++; // Increase the depth on hitting a start tag

            isInitTagEnded = true;
            *(tag + tagpos) = '\0'; // 1. Null-terminate BEFORE trimming
            trim_whitespace(tag);   // 2. Strip spaces cleanly
            tagpos = strlen(tag);   // 3. Reset to precise string length
            // Copy to pure tag
            copyTagPure(tag, tagpos, tagpure, paramstr);
            // printf("Pure Tag:%s\n",tagpure);
        }
        else if (isInitTagStarted == true && isInitTagEnded == false)
        {
            *(tag + tagpos) = charecter;
            tagpos++;
        }
        else if (charecter == '<' && isInsideQuote==false && isInitTagEnded == true)
        {
            isEndTagStarted = true;
        }
        else if (isInitTagStarted == true && isInitTagEnded == true && isEndTagStarted == false)
        {
            *(innerHTML + htmlpos) = charecter;
            htmlpos++;
        }
        else if (charecter == '>' && isInsideQuote==false && isEndTagStarted == true)
        {

            *(Endtag + Endtagpos) = '\0'; // 1. Null-terminate BEFORE checking!
            trim_whitespace(Endtag);      // 2. Clean out trailing spaces
            Endtagpos = strlen(Endtag);   // 3. Reset index length

            //printf("Endtag got=%s Inittag=%s\n", Endtag, tagpure);

            if (compareRawstr(tagpure, Endtag, strlen(tagpure), Endtagpos) == true && isEndslashgot == true)
            {
               // printf("Current tag stack:%d\n", tagStack);

                if (tagStack == 1)
                {
                    //printf("Matching tag found for:%s=%s\n", tagpure, Endtag);
                    isEndTagEnded = true;
                    *(contentprocessed + contentlen) = charecter;
                    contentlen++; // Accurately count the final '>' found inside the loop boundary
                    break;
                }
                else
                {
                    // It is not the actual ending tag
                    //printf("This is the impostor tag skip it....\n");
                    isEndslashgot = false;

                    *(innerHTML + htmlpos) = '<';
                    htmlpos++;

                    *(innerHTML + htmlpos) = '/';
                    htmlpos++;

                    for (int i = 0; i < Endtagpos; i++)
                    {
                        *(innerHTML + htmlpos) = *(Endtag + i);
                        *(Endtag + i) = ' ';
                        htmlpos++;
                    }

                    *(innerHTML + htmlpos) = '>';
                    htmlpos++;

                    Endtagpos = 0;
                    offset++;

                    tagStack--; // Reduce it as one of closing tag is encountered....
                }
            }
            else
            {

                isEndTagEnded = false;
                isEndTagStarted = false;

                *(innerHTML + htmlpos) = '<';
                htmlpos++;

                if (isEndslashgot == false)
                {
                    //printf("Copying from opentag...\n");


                    char pureOpen[opentagtemppos + 1];
                    char paramOpen[opentagtemppos + 1];

            
                    *(Opentagtemp + opentagtemppos) = '\0'; // 1. Null-terminate BEFORE trimming

                    trim_whitespace(Opentagtemp);   // 2. Strip spaces cleanly
                    tagpos = strlen(Opentagtemp);   // 3. Reset to precise string length
                    // Copy to pure tag
                    copyTagPure(Opentagtemp, opentagtemppos, pureOpen, paramOpen);


                    if (compareRawstr(tagpure, pureOpen, strlen(tagpure), strlen(pureOpen)))
                    {

                        //printf("Found same tag in opentag\n");
                        tagStack++; // Increase it one opening tag of same type of start tag is encountered....
                    }

                    for (int i = 0; i < opentagtemppos; i++)
                    {

                        *(innerHTML + htmlpos) = *(Opentagtemp + i);
                        *(Opentagtemp + i) = ' ';
                        htmlpos++;
                    }

                    *(innerHTML + htmlpos) = '>';
                    htmlpos++;

                    opentagtemppos = 0;
                    offset++;
                }
                else
                {
                    isEndslashgot = false;
                    *(innerHTML + htmlpos) = '/';
                    htmlpos++;

                    for (int i = 0; i < Endtagpos; i++)
                    {
                        *(innerHTML + htmlpos) = *(Endtag + i);
                        *(Endtag + i) = ' ';
                        htmlpos++;
                    }

                    *(innerHTML + htmlpos) = '>';
                    htmlpos++;

                    Endtagpos = 0;
                    offset++;
                }
            }
        }
        else if (isEndTagStarted == true && isEndTagEnded == false)
        {
            if (isEndslashgot == false && charecter == '/' && isInsideQuote == false)
            {
                // printf("Got the slash\n");
                isEndslashgot = true;
                *(contentprocessed + contentlen) = charecter;
                contentlen++;
                continue;
            }

            if (isEndslashgot == true)
            {
                //printf("Writing to end tag:%c\n", charecter);
                *(Endtag + Endtagpos) = charecter;
                Endtagpos++;
            }
            else
            {
                //printf("Writing to temp open tag buffer:%c\n", charecter);
                *(Opentagtemp + opentagtemppos) = charecter;
                opentagtemppos++;
            }
        }

        *(contentprocessed + contentlen) = charecter;
        contentlen++;
        // printf("Came here in loop:%c\n",charecter);
    }

    // Terminate strings safely
    *(innerHTML + htmlpos) = '\0';
    *(tag + tagpos) = '\0';
    *(Endtag + Endtagpos) = '\0';
    *(contentprocessed + contentlen) = '\0';

    //printf("Came here out of loop\n");
    //Wprintf("Content processed:%s\n", contentprocessed);
    //printf("Tag:%s\n", tag);
    //printf("Inner html:%s\n", innerHTML);
    

    DOMNode *newNode = (DOMNode *)malloc(sizeof(DOMNode));
    newNode->firstChild = NULL;
    newNode->nextSibling = NULL;
    newNode->isLeaf = false;
    newNode->isRoot = false;

    if (isFirst == true)
    {
        upline->firstChild = newNode;
    }
    else
    {
        upline->nextSibling = newNode;
    }

    // Leaf Node Handler
    if (tagpos == 0 && htmlpos == 0 && Endtagpos == 0)
    {
        // Use pointer arithmetic to read from the actual slice offset
        // printf("InnerHTML=%s\n", htmlContent + startPointer);
        // printf("This is the leaf node\n");
        // printf("Total depth:%d\n", depth + 1);

        newNode->isLeaf = true;
        newNode->tag = strdup("TEXT");
        newNode->innerText = strdup(htmlContent + startPointer);

        // Safeguard text elements
        newNode->attrcount = 0;
        newNode->attrKey = NULL;
        newNode->attrVal = NULL;

        free(tag);
        free(tagpure);
        free(innerHTML);
        free(paramstr);
        free(Endtag);
        free(contentprocessed);
        free(Opentagtemp);
        return;
    }
    else
    {
        // printf("InnerHTML=%s\n", innerHTML);
        // printf("Tag of HTML=%s\n", tagpure);
        // printf("Depth: %d\n", depth + 1);

        TagParser(paramstr, strlen(paramstr), newNode);

        newNode->tag = strdup(tagpure);
        newNode->innerText = strdup(innerHTML);

        // Compute the clean, precise start point for the next sibling element
        int nextSiblingIndex = startPointer + contentlen;

        if (nextSiblingIndex < (int)strlen(htmlContent))
        {
            // printf("======================================\n");
            Parser(htmlContent, nextSiblingIndex, depth, false, newNode);
        }
        // printf("======================================\n");

        int depth_new = depth + 1;
        Parser(innerHTML, 0, depth_new, true, newNode);

        free(tag);
        free(innerHTML);
        free(tagpure);
        free(paramstr);
        free(Endtag);
        free(contentprocessed);
        free(Opentagtemp);
    }
}


// This replaces your standard int main() block
DLL_EXPORT DOMNode* parse_xml_to_tree(const char *xmlContent) {
    if (xmlContent == NULL) return NULL;

    // Allocate a persistent root node on the C Heap so Python can hold onto it
    DOMNode *root = (DOMNode *)malloc(sizeof(DOMNode));
    if (!root) return NULL;

    root->isRoot = true;
    root->isLeaf = false;
    root->firstChild = NULL;
    root->nextSibling = NULL;
    root->tag = strdup("ROOT");
    root->innerText = strdup("");
    root->attrcount = 0;
    root->attrKey = NULL;
    root->attrVal = NULL;

    // Use a non-const mirror copy because your internal string manipulation trims tokens
    char *mirror_copy = strdup(xmlContent);
    
    // Kickstart your native engine parser line
    Parser(mirror_copy, 0, 0, true, root);

    free(mirror_copy);
    return root; // Hand the raw memory address pointer directly up to Python!
}

// Export your memory cleanup function so Python can safely clear allocations
DLL_EXPORT void free_c_tree(DOMNode *root) {
    if (root != NULL) {
        freeDOMTree(root);
    }
}

