#include <stdio.h>
#include <string.h>
#include <stdbool.h>
#include <stdlib.h> // Required for malloc
#include <ctype.h>  // Required for isspace()

typedef struct DOMNode
{
    // 1. Data Fields
    char *tag; // Stores the tag pointer (e.g., "div", "p", "h1")

    int attrcount;

    char **attrKey;  // Stores the attribute pointer (e.g., "width", "id")
    char **attrVal;  // Stores the attribute pointer (e.g., "100", "main")
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

void copyTagPure(char tag[], int size, char *copyTo, char *paramsstring)
{

    int blankspace = 0;
    int copytosize = 0;
    int copyparamstrsize = 0;
    bool copytoparamsstr = false;
    for (int i = 0; i < size; i++)
    {
        char cont = tag[i];
        if (cont == ' ')
        {
            blankspace++;

            if (blankspace == 1)
            {
                copytoparamsstr = true;
            }
            if (copytoparamsstr == true)
            {
                *(paramsstring + copyparamstrsize) = cont;
                copyparamstrsize++;
            }
        }
        else
        {
            if (copytoparamsstr == true)
            {
                *(paramsstring + copyparamstrsize) = cont;
                copyparamstrsize++;
            }
            else
            {
                *(copyTo + copytosize) = cont;
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
    printf(paramsstring);
    
    char buffer[size + 1];
    int buffsize = 0;

    bool istagprocessed = false;
    bool isparsingParamkey = true;
    bool isparsingParamValue = false;
    bool paramskeyinit = false;
    bool insidequote = false;
    char startchar = ' ';

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

                        printf("Debug:params value recording stopped...\n");
                        // stop it
                        isparsingParamValue = false;
                        isparsingParamkey = true;
                        paramskeyinit = false;
                        insidequote = false;

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
                    printf("Debug:value recording started..\n");
                    startchar = content; // Store the current char so that we can match it in time of the closing
                    paramskeyinit = true;
                    insidequote = true;
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
                printf("DEBUG:The value is:%s\n", value[i]);
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

void freeDOMTree(DOMNode *node)
{
    if (node == NULL)
        return;

    // 1. Recursively clear branches down and sideways
    freeDOMTree(node->firstChild);
    freeDOMTree(node->nextSibling);

    // 2. Free internal attribute arrays
    for (int i = 0; i < node->attrcount; i++)
    {
        free(node->attrKey[i]);
        free(node->attrVal[i]);
    }
    if (node->attrcount > 0)
    {
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

    bool isInsideQuote = false;
    char quotechar;

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

        if (charecter == '<' && isInsideQuote == false && isInitTagStarted == false)
        {
            isInitTagStarted = true;
        }
        else if (charecter == '>' && isInsideQuote == false && isInitTagStarted == true && isEndTagStarted == false)
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
        else if (charecter == '<' && isInsideQuote == false && isInitTagEnded == true)
        {
            isEndTagStarted = true;
        }
        else if (isInitTagStarted == true && isInitTagEnded == true && isEndTagStarted == false)
        {
            *(innerHTML + htmlpos) = charecter;
            htmlpos++;
        }
        else if (charecter == '>' && isInsideQuote == false && isEndTagStarted == true)
        {

            *(Endtag + Endtagpos) = '\0'; // 1. Null-terminate BEFORE checking!
            trim_whitespace(Endtag);      // 2. Clean out trailing spaces
            Endtagpos = strlen(Endtag);   // 3. Reset index length

            // printf("Endtag got=%s Inittag=%s\n", Endtag, tagpure);

            if (compareRawstr(tagpure, Endtag, strlen(tagpure), Endtagpos) == true && isEndslashgot == true)
            {
                // printf("Current tag stack:%d\n", tagStack);

                if (tagStack == 1)
                {
                    // printf("Matching tag found for:%s=%s\n", tagpure, Endtag);
                    isEndTagEnded = true;
                    *(contentprocessed + contentlen) = charecter;
                    contentlen++; // Accurately count the final '>' found inside the loop boundary
                    break;
                }
                else
                {
                    // It is not the actual ending tag
                    // printf("This is the impostor tag skip it....\n");
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
                    char pureOpen[opentagtemppos + 1];
                    char paramOpen[opentagtemppos + 1];

                    *(Opentagtemp + opentagtemppos) = '\0'; // 1. Null-terminate BEFORE trimming

                    trim_whitespace(Opentagtemp);   // 2. Strip spaces cleanly
                    
                    // 3. Get the precise string length AFTER trimming
                    int clean_length = strlen(Opentagtemp);   
                    
                    // FIX 1: Pass the clean_length, not the stale opentagtemppos
                    copyTagPure(Opentagtemp, clean_length, pureOpen, paramOpen);

                    if (compareRawstr(tagpure, pureOpen, strlen(tagpure), strlen(pureOpen)))
                    {
                        tagStack++; 
                    }

                    // FIX 2: Loop using clean_length so you don't inject \0 into innerHTML!
                    for (int i = 0; i < clean_length; i++)
                    {
                        *(innerHTML + htmlpos) = *(Opentagtemp + i);
                        *(Opentagtemp + i) = ' '; // clear it out
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
                // printf("Writing to end tag:%c\n", charecter);
                *(Endtag + Endtagpos) = charecter;
                Endtagpos++;
            }
            else
            {
                // printf("Writing to temp open tag buffer:%c\n", charecter);
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

    

    if (isInsideQuote == true)
    {
        // Force the tag name to be an unregistered string.
        // Your Python compiler will intercept this and throw the SyntaxError!
        strcpy(tagpure, "FATAL_CORRUPTION_UNCLOSED_QUOTE");
    }
    

    // printf("Came here out of loop\n");
    // printf("Content processed:%s\n", contentprocessed);
    // printf("Tag:%s\n", tagpure);
    // printf("Inner html:%s\n", innerHTML);

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

void printDOMTree(DOMNode *node, int level)
{
    if (node == NULL)
        return;

    // 1. Create a dynamic visual indentation spacing based on tree depth
    for (int i = 0; i < level; i++)
    {
        printf("  ");
    }

    // 2. Print Node Information
    if (node->isLeaf)
    {
        printf("[TEXT] -> \"%s\"\n", node->innerText);
    }
    else
    {
        printf("<%s", node->tag);

        // Loop through and cleanly display every captured multi-attribute pair!
        for (int i = 0; i < node->attrcount; i++)
        {
            printf(" %s=\"%s\"", node->attrKey[i], node->attrVal[i]);
        }
        printf(">\n");
    }

    // 3. Move recursively DOWN into children first
    printDOMTree(node->firstChild, level + 1);

    // 4. Move recursively SIDEWAYS into siblings at the same depth level
    printDOMTree(node->nextSibling, level);
}

int main(int argc, char const *argv[])
{
    char html[1024];

    printf("Enter html Expression:");
    fgets(html, sizeof(html), stdin);

    html[strcspn(html, "\n")] = '\0';

    DOMNode root;
    root.isRoot = true;
    root.firstChild = NULL;
    root.nextSibling = NULL;
    root.tag = "ROOT";
    root.attrcount = 0;

    Parser(html, 0, 0, true, &root);

    // =========================================================
    // VISUAL VERIFICATION: Print out the tree we built!
    // =========================================================
    printf("\n======= PARSED DOM TREE STRUCTURE =======\n");
    printDOMTree(root.firstChild, 0);
    printf("=========================================\n");

    // Clean up memory before program exit
    freeDOMTree(root.firstChild);

    return 0;
}