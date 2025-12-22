
import Text from "@tiptap/extension-text";
import CodeBlock from '@tiptap/extension-code-block'
import Document from '@tiptap/extension-document'
import Paragraph from '@tiptap/extension-paragraph'
import Bold from '@tiptap/extension-bold'
import Image from "@tiptap/extension-image";
import Heading from '@tiptap/extension-heading'
import { Dropcursor } from '@tiptap/extensions'
import { EditorContent, useEditor, EditorContext } from "@tiptap/react";
import {
    Paper,
    Toolbar,
    IconButton,
    Box,
    Tooltip
} from '@mui/material';
import { Code as CodeIcon } from '@mui/icons-material';
import FormatBoldIcon from '@mui/icons-material/FormatBold';
import ImageIcon from '@mui/icons-material/Image';


function ContentEditor({ initialContent, contentUpdateCallback }) {
    const editor = useEditor({
        extensions: [
            Document,
            Paragraph,
            Text,
            CodeBlock,
            Bold,
            Image.configure({
                allowBase64: false,
                resize: {
                    enabled: true,
                    alwaysPreserveAspectRatio: true,
                },
            }),
            Heading.configure({
                levels: [1, 2, 3],
            }),
            Dropcursor,],
        content: initialContent,
        autofocus: true,
        onUpdate: ({ editor }) => {
            contentUpdateCallback(editor.getHTML());
        },
    })

    if (!editor) {
        return null
    }

    return (
        <Paper elevation={2} sx={{ width: '100%' }}>
            <EditorContext.Provider value={{ editor }}>
                {/* Material UI Toolbar */}
                <Toolbar variant="dense" sx={{
                    backgroundColor: 'grey.50',
                    borderBottom: '1px solid',
                    borderColor: 'divider'
                }}>
                    <IconButton
                        onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
                        size="small"
                        sx={{ fontSize: '16px' }}
                    >
                        H1
                    </IconButton>
                    <IconButton
                        onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
                        size="small"
                        sx={{ fontSize: '14px' }}
                    >
                        H2
                    </IconButton>
                    <IconButton
                        onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
                        size="small"
                        sx={{ fontSize: '12px' }}
                    >
                        H3
                    </IconButton> |
                    <Tooltip title="Bold" placement="top">
                    <IconButton
                        onClick={() => editor.chain().focus().toggleBold().run()}
                        size="small"
                    >
                        <FormatBoldIcon />
                    </IconButton>
                    </Tooltip>
                    <Tooltip title="Insert Image" placement="top">
                    <IconButton
                        onClick={() => {
                            const url = window.prompt('Enter image URL');
                            if (url) {
                                editor.chain().focus().setImage({ src: url }).run();
                            }
                        }}
                        size="small"
                        label="Insert Image"
                    >
                        <ImageIcon />
                    </IconButton>
                    </Tooltip>
                    <Tooltip title="Code Block" placement="top">
                    <IconButton
                        onClick={() => editor.chain().focus().toggleCodeBlock().run()}
                        size="small"
                        label="Code Block"
                    >
                        <CodeIcon />
                    </IconButton>
                    </Tooltip>
                </Toolbar>

                {/* TipTap Editor wrapped in Material UI Box */}
                <Box
                    sx={{
                        width: '100%',
                        '& .ProseMirror': {
                            paddingTop: 2,
                            paddingLeft: 4,
                            paddingRight: 4,
                            paddingBottom: 2,
                            minHeight: 200,
                            outline: 'none',
                            fontSize: '16px',
                            lineHeight: 1.6,
                            fontFamily: 'Roboto, Arial, sans-serif',
                            '& p': {
                                margin: '0 0 16px 0',
                                '&:last-child': {
                                    marginBottom: 0
                                }
                            },
                            '& pre': {
                                backgroundColor: 'grey.100',
                                borderRadius: 1,
                                padding: 2,
                                margin: '16px 0',
                                fontFamily: 'Monaco, Consolas, monospace',
                                fontSize: '14px',
                                border: '1px solid',
                                borderColor: 'grey.300'
                            },
                            '& strong': {
                                fontWeight: 'bold'
                            }
                        }
                    }}
                >
                    <EditorContent editor={editor} />
                </Box>
            </EditorContext.Provider>
        </Paper>
    );
}

export default ContentEditor
