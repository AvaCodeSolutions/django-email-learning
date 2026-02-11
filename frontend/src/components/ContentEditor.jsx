
import Text from '@tiptap/extension-text'
import CodeBlock from '@tiptap/extension-code-block'
import Document from '@tiptap/extension-document'
import Paragraph from '@tiptap/extension-paragraph'
import Bold from '@tiptap/extension-bold'
import Italic from '@tiptap/extension-italic'
import Link from '@tiptap/extension-link'
import BlockQuote from '@tiptap/extension-blockquote'
import { BulletList, ListItem } from '@tiptap/extension-list'
import InsertLinkIcon from '@mui/icons-material/InsertLink'
import FormatQuoteIcon from '@mui/icons-material/FormatQuote'
import FormatListBulletedIcon from '@mui/icons-material/FormatListBulleted'
import AlignHorizontalRightIcon from '@mui/icons-material/AlignHorizontalRight'
import AlignHorizontalLeftIcon from '@mui/icons-material/AlignHorizontalLeft'
import FormatAlignCenterIcon from '@mui/icons-material/FormatAlignCenter'
import TextAlign from '@tiptap/extension-text-align'
import Image from "@tiptap/extension-image";
import Heading from '@tiptap/extension-heading'
import { Dropcursor } from '@tiptap/extensions'
import { EditorContent, useEditor, EditorContext } from "@tiptap/react"
import {
    Paper,
    Toolbar,
    IconButton,
    Box,
    Tooltip
} from '@mui/material';
import { Code as CodeIcon } from '@mui/icons-material';
import FormatBoldIcon from '@mui/icons-material/FormatBold';
import FormatItalicIcon from '@mui/icons-material/FormatItalic';
import ImageIcon from '@mui/icons-material/Image';


function ContentEditor({ initialContent, contentUpdateCallback, disabled = false }) {
    const editor = useEditor({
        extensions: [
            Document,
            Paragraph,
            Text,
            CodeBlock,
            Bold,
            BlockQuote,
            BulletList,
            ListItem,
            Italic,
            Link,
            TextAlign.configure({
                types: ['paragraph', 'heading'],
            }),
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
        editable: !disabled,
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
                {!disabled && <Toolbar variant="dense" sx={{
                    backgroundColor: 'background.nav',
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
                    <Tooltip title="Italic" placement="top">
                    <IconButton
                        onClick={() => editor.chain().focus().toggleItalic().run()}
                        size="small"
                    >
                        <FormatItalicIcon />
                    </IconButton>
                    </Tooltip>
                    <Tooltip title="Bullet List" placement="top">
                    <IconButton
                        onClick={() => editor.chain().focus().toggleBulletList().run()}
                        size="small"
                    >
                        <FormatListBulletedIcon />
                    </IconButton>
                    </Tooltip>
                    <Tooltip title="Align Left" placement="top">
                    <IconButton
                        onClick={() => editor.chain().focus().setTextAlign('left').run()}
                        size="small"
                    >
                        <AlignHorizontalLeftIcon />
                    </IconButton>
                    </Tooltip>
                    <Tooltip title="Align Center" placement="top">
                    <IconButton
                        onClick={() => editor.chain().focus().setTextAlign('center').run()}
                        size="small"
                    >
                        <FormatAlignCenterIcon />
                    </IconButton>
                    </Tooltip>
                    <Tooltip title="Align Right" placement="top">
                    <IconButton
                        onClick={() => editor.chain().focus().setTextAlign('right').run()}
                        size="small"
                    >
                        <AlignHorizontalRightIcon />
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
                    <Tooltip title="Insert Link" placement="top">
                    <IconButton
                        onClick={() => {
                            if (editor.isActive('link')) {
                                const currentHref = editor.getAttributes('link').href || '';
                                const url = window.prompt('Update URL (leave empty to remove)', currentHref);
                                if (!url) {
                                    editor.chain().focus().unsetLink().run();
                                    return;
                                }
                                editor.chain().focus().extendMarkRange('link').setLink({ href: url }).run();
                                return;
                            }
                            const url = window.prompt('Enter URL');
                            if (url) {
                                editor.chain().focus().toggleLink({ href: url }).run();
                            }
                        }}
                        size="small"
                        label="Insert Link"
                    >
                        <InsertLinkIcon />
                    </IconButton>
                    </Tooltip>
                    <Tooltip title="Block Quote" placement="top">
                    <IconButton
                        onClick={() => editor.chain().focus().toggleBlockquote().run()}
                        size="small"
                        label="Block Quote"
                    >
                        <FormatQuoteIcon />
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
                </Toolbar>}

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
                                backgroundColor: 'grey.50',
                                borderRadius: 1,
                                padding: 2,
                                margin: '16px 0',
                                fontFamily: 'Monaco, Consolas, monospace',
                                fontSize: '14px',
                                border: '1px solid',
                                borderColor: 'grey.100'
                            },
                            '& strong': {
                                fontWeight: 'bold'
                            },
                            'blockquote': {
                                borderLeft: direction == 'rtl' ? 'none' : '4px solid',
                                borderRight: direction == 'rtl' ? '4px solid' : 'none',
                                margin: '0px !important',
                                padding: '0 16px',
                                borderColor: 'grey.100',

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
