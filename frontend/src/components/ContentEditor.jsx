
import { useEffect, useState } from 'react';
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
import AssistantIcon from '@mui/icons-material/Assistant';
import LinkOffIcon from '@mui/icons-material/LinkOff';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import UndoIcon from '@mui/icons-material/Undo';
import RedoIcon from '@mui/icons-material/Redo';
import TextAlign from '@tiptap/extension-text-align'
import Image from "@tiptap/extension-image";
import Heading from '@tiptap/extension-heading'
import { Dropcursor, UndoRedo } from '@tiptap/extensions'
import { DOMSerializer } from '@tiptap/pm/model'
import { EditorContent, useEditor, EditorContext } from "@tiptap/react"
import { BubbleMenu } from "@tiptap/react/menus"
import {
    Paper,
    Toolbar,
    IconButton,
    Box,
    CircularProgress,
    Tooltip,
    Button
} from '@mui/material';
import { Code as CodeIcon } from '@mui/icons-material';
import FormatBoldIcon from '@mui/icons-material/FormatBold';
import FormatItalicIcon from '@mui/icons-material/FormatItalic';
import ImageIcon from '@mui/icons-material/Image';
import VerticalAlignCenterIcon from '@mui/icons-material/VerticalAlignCenter';
import { useAppContext } from '../render'
import { getCookie } from '../utils.js';
import { ChaoticOrbit } from 'ldrs/react'
import 'ldrs/react/ChaoticOrbit.css'


function ContentEditor({ initialContent, contentUpdateCallback, disabled = false, extraMinLines = 0, editorInstanceCallback, defaultDirection }) {
    const {
        direction: appDirection,
        apiBaseUrl,
        localeMessages,
        userRole,
        aiTextEditModel,
        aiTextEditingModel,
    } = useAppContext();
    const direction = defaultDirection || appDirection;
    const configuredAiModel = aiTextEditModel || aiTextEditingModel;
    const hasAiPermission = userRole === 'admin' || userRole === 'editor';
    const hasAiFeatureEnabled = Boolean(configuredAiModel);
    const aiBaseUrl = apiBaseUrl?.includes('/api/platform')
        ? apiBaseUrl.replace('/api/platform', '/api/ai')
        : '/email_learning/api/ai';
    const defaultTextAlign = direction === 'rtl' ? 'right' : 'left';
    const minHeight = 200 + (Math.max(0, extraMinLines) * 24);
    const [editorHeight, setEditorHeight] = useState(minHeight);
    const [aiEditLoading, setAiEditLoading] = useState(false);

    useEffect(() => {
        setEditorHeight((previousHeight) => Math.max(previousHeight, minHeight));
    }, [minHeight]);

    const handleResizeStart = (event) => {
        event.preventDefault();
        const startY = event.clientY;
        const startHeight = editorHeight;

        const onMouseMove = (moveEvent) => {
            const deltaY = moveEvent.clientY - startY;
            setEditorHeight(Math.max(minHeight, startHeight + deltaY));
        };

        const onMouseUp = () => {
            document.body.style.userSelect = '';
            document.body.style.cursor = '';
            window.removeEventListener('mousemove', onMouseMove);
            window.removeEventListener('mouseup', onMouseUp);
        };

        document.body.style.userSelect = 'none';
        document.body.style.cursor = 'ns-resize';
        window.addEventListener('mousemove', onMouseMove);
        window.addEventListener('mouseup', onMouseUp);
    };

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
            Link.configure({
                openOnClick: disabled,
                enableClickSelection: true,
            }),
            TextAlign.configure({
                types: ['paragraph', 'heading'],
            }),
            Image.configure({
                allowBase64: false,
                inline: true,
                resize: {
                    enabled: true,
                    alwaysPreserveAspectRatio: true,
                },
            }),
            Heading.configure({
                levels: [1, 2, 3],
            }),
            UndoRedo,
            Dropcursor,],
        content: initialContent,
        editable: !disabled,
        autofocus: true,
        editorProps: {
            attributes: {
                dir: direction,
                style: `text-align: ${defaultTextAlign};`,
            },
        },
        onUpdate: ({ editor }) => {
            contentUpdateCallback(editor.getHTML());
        },
    })

    useEffect(() => {
        if (editorInstanceCallback) {
            editorInstanceCallback(editor || null);
        }

        return () => {
            if (editorInstanceCallback) {
                editorInstanceCallback(null);
            }
        };
    }, [editor, editorInstanceCallback]);

    if (!editor) {
        return null
    }

    const applyAlignment = (align) => {
        if (editor.isActive('image')) {
            const isAppliedToParagraph = editor.chain().focus().updateAttributes('paragraph', { textAlign: align }).run();
            if (isAppliedToParagraph) {
                return;
            }
        }
        editor.chain().focus().setTextAlign(align).run();
    };

    const openActiveLinkInNewTab = () => {
        const href = editor.getAttributes('link').href;
        if (!href) {
            return;
        }
        window.open(href, '_blank', 'noopener,noreferrer');
    };

    const unlinkActiveLink = () => {
        editor.chain().focus().extendMarkRange('link').unsetLink().run();
    };

    const getActiveOrganizationId = () => {
        if (typeof window === 'undefined') {
            return null;
        }
        return window.localStorage.getItem('activeOrganizationId');
    };

    const getSelectedTextForAi = (activeEditor) => {
        const { selection, doc } = activeEditor.state;
        const { from, to, empty } = selection;
        if (empty) {
            return null;
        }

        const selectedText = doc.textBetween(from, to, '\n', '\n');
        const normalizedText = selectedText.trim();
        const hasNoNewLine = !selectedText.includes('\n') && !selectedText.includes('\r');
        const isWithinCharLimit = normalizedText.length >= 40 && normalizedText.length <= 500;
        const $from = doc.resolve(from);
        const $to = doc.resolve(to);
        const isSameParagraph = $from.sameParent($to) && $from.parent.type.name === 'paragraph';
        const isWholeParagraphSelected = isSameParagraph
            && from === $from.start()
            && to === $from.end();

        if (!hasNoNewLine || !isWithinCharLimit || !isWholeParagraphSelected) {
            return null;
        }

        const selectionSlice = activeEditor.state.selection.content();
        const serializer = DOMSerializer.fromSchema(activeEditor.state.schema);
        const wrapper = document.createElement('div');
        wrapper.appendChild(serializer.serializeFragment(selectionSlice.content));
        const textWithMarkup = wrapper.innerHTML.trim();

        return {
            from,
            to,
            text: normalizedText,
            textWithMarkup,
        };
    };

    const canShowAiEditBubbleMenu = (activeEditor) => {
        if (disabled || aiEditLoading) {
            return false;
        }
        if (!hasAiPermission || !hasAiFeatureEnabled) {
            return false;
        }
        if (!getActiveOrganizationId()) {
            return false;
        }
        if (!activeEditor.isFocused || activeEditor.isActive('link')) {
            return false;
        }
        return Boolean(getSelectedTextForAi(activeEditor));
    };

    const normalizeAiEditedMarkup = (editedText) => {
        if (typeof editedText !== 'string') {
            return editedText;
        }

        const wrapper = document.createElement('div');
        wrapper.innerHTML = editedText.trim();
        if (wrapper.children.length !== 1) {
            return editedText;
        }

        const rootTag = wrapper.firstElementChild?.tagName;
        if (!rootTag) {
            return editedText;
        }

        // Prevent duplicate block wrappers (e.g. ul-in-ul) when replacing inside an existing block context.
        if (['UL', 'OL', 'P'].includes(rootTag)) {
            return wrapper.firstElementChild.innerHTML;
        }

        return editedText;
    };

    const editSelectionWithAi = async () => {
        const selection = getSelectedTextForAi(editor);
        const organizationId = getActiveOrganizationId();
        if (!selection || !organizationId || aiEditLoading) {
            return;
        }

        setAiEditLoading(true);
        try {
            const response = await fetch(
                `${aiBaseUrl}/organizations/${organizationId}/edit-text/`,
                {
                    method: 'POST',
                    credentials: 'include',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken'),
                    },
                    body: JSON.stringify({
                        input: selection.textWithMarkup || selection.text,
                    }),
                },
            );
            const data = await response.json();
            if (!response.ok || !data.edited_text) {
                console.error('AI text editing failed:', data.error || 'Unexpected AI edit response');
                return;
            }

            const normalizedEditedText = normalizeAiEditedMarkup(data.edited_text);

            editor
                .chain()
                .focus()
                .insertContentAt({ from: selection.from, to: selection.to }, normalizedEditedText)
                .setTextSelection(selection.from + String(normalizedEditedText).length)
                .run();
        } catch (error) {
            console.error('AI text editing request failed:', error);
        } finally {
            setAiEditLoading(false);
        }
    };

    const canUndo = editor.can().chain().focus().undo().run();
    const canRedo = editor.can().chain().focus().redo().run();

    return (
        <Paper elevation={2} sx={{ width: '100%' }}>
            <EditorContext.Provider value={{ editor }}>
                {/* Material UI Toolbar */}
                {!disabled && <Toolbar variant="dense" sx={{
                    backgroundColor: 'background.nav',
                    borderBottom: '1px solid',
                    borderColor: 'divider',
                    position: 'sticky',
                    top: 0,
                    zIndex: 10
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
                    <Tooltip title="Undo" placement="top">
                    <IconButton
                        onClick={() => editor.chain().focus().undo().run()}
                        size="small"
                        disabled={!canUndo}
                    >
                        <UndoIcon />
                    </IconButton>
                    </Tooltip>
                    <Tooltip title="Redo" placement="top">
                    <IconButton
                        onClick={() => editor.chain().focus().redo().run()}
                        size="small"
                        disabled={!canRedo}
                    >
                        <RedoIcon />
                    </IconButton>
                    </Tooltip>
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
                        onClick={() => applyAlignment('left')}
                        size="small"
                    >
                        <AlignHorizontalLeftIcon />
                    </IconButton>
                    </Tooltip>
                    <Tooltip title="Align Center" placement="top">
                    <IconButton
                        onClick={() => applyAlignment('center')}
                        size="small"
                    >
                        <FormatAlignCenterIcon />
                    </IconButton>
                    </Tooltip>
                    <Tooltip title="Align Right" placement="top">
                    <IconButton
                        onClick={() => applyAlignment('right')}
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
                        position: 'relative',
                        '& .ProseMirror': {
                            paddingTop: 2,
                            paddingLeft: 4,
                            paddingRight: 4,
                            paddingBottom: 2,
                            minHeight: editorHeight,
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
                                backgroundColor: (theme) => theme.palette.mode === 'dark' ? 'grey.700' : 'grey.50',
                                borderRadius: 1,
                                padding: 2,
                                margin: '16px 0',
                                fontFamily: 'Monaco, Consolas, monospace',
                                fontSize: '14px',
                                border: '1px solid',
                                borderColor: (theme) => theme.palette.mode === 'dark' ? 'grey.800' : 'grey.100'
                            },
                            '& strong': {
                                fontWeight: 'bold'
                            },
                            '& a': {
                                color: (theme) => theme.palette.mode === 'dark' ? theme.palette.primary.light : theme.palette.primary.main,
                                textDecorationColor: (theme) => theme.palette.mode === 'dark' ? theme.palette.primary.light : theme.palette.primary.main,
                                '&:hover': {
                                    color: (theme) => theme.palette.mode === 'dark' ? theme.palette.primary.light : theme.palette.primary.main,
                                },
                            },
                            '& img': {
                                display: 'inline-block',
                                maxWidth: '100%',
                                height: 'auto',
                                marginTop: 4,
                                marginBottom: 4,
                            },
                            '& [data-resize-wrapper]': {
                                display: 'inline-block',
                                maxWidth: '100%',
                            },
                            '& p[style*="text-align: left"] [data-resize-wrapper], & h1[style*="text-align: left"] [data-resize-wrapper], & h2[style*="text-align: left"] [data-resize-wrapper], & h3[style*="text-align: left"] [data-resize-wrapper]': {
                                display: 'block',
                                width: 'fit-content',
                                marginLeft: 0,
                                marginRight: 'auto',
                            },
                            '& p[style*="text-align: center"] [data-resize-wrapper], & h1[style*="text-align: center"] [data-resize-wrapper], & h2[style*="text-align: center"] [data-resize-wrapper], & h3[style*="text-align: center"] [data-resize-wrapper]': {
                                display: 'block',
                                width: 'fit-content',
                                marginLeft: 'auto',
                                marginRight: 'auto',
                            },
                            '& p[style*="text-align: right"] [data-resize-wrapper], & h1[style*="text-align: right"] [data-resize-wrapper], & h2[style*="text-align: right"] [data-resize-wrapper], & h3[style*="text-align: right"] [data-resize-wrapper]': {
                                display: 'block',
                                width: 'fit-content',
                                marginLeft: 'auto',
                                marginRight: 0,
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
                    {!disabled && (
                        <BubbleMenu
                            pluginKey="link-bubble-menu"
                            editor={editor}
                            shouldShow={({ editor: activeEditor, state }) => (
                                activeEditor.isFocused
                                && activeEditor.isActive('link')
                                && !state.selection.empty
                            )}
                            updateDelay={0}
                            options={{
                                duration: 0,
                                placement: 'top-start',
                                animation: false,
                                zIndex: 1500,
                            }}
                        >
                            <Paper
                                elevation={2}
                                sx={{
                                    position: 'relative',
                                    zIndex: 1500,
                                    display: 'flex',
                                    gap: 1,
                                    p: 0.75,
                                    border: '1px solid',
                                    borderColor: 'divider',
                                }}
                            >
                                <Button
                                    size="small"
                                    variant="text"
                                    sx={{ color: 'primary.dark' }}
                                    startIcon={<OpenInNewIcon />}
                                    onMouseDown={(event) => event.preventDefault()}
                                    onClick={openActiveLinkInNewTab}
                                >
                                    Open Link
                                </Button>
                                <Button
                                    size="small"
                                    variant="text"
                                    sx={{ color: 'primary.dark' }}
                                    startIcon={<LinkOffIcon />}
                                    onMouseDown={(event) => event.preventDefault()}
                                    onClick={unlinkActiveLink}
                                >
                                    Unlink
                                </Button>
                            </Paper>
                        </BubbleMenu>
                    )}
                    {!disabled && (
                        <BubbleMenu
                            pluginKey="ai-edit-bubble-menu"
                            editor={editor}
                            shouldShow={({ editor: activeEditor }) => canShowAiEditBubbleMenu(activeEditor)}
                            updateDelay={400}
                            options={{
                                duration: 0,
                                placement: 'top',
                                animation: false,
                                delay: [0, 0],
                                zIndex: 1500,
                            }}
                        >
                            <Paper
                                elevation={2}
                                sx={{
                                    position: 'relative',
                                    zIndex: 1500,
                                    display: 'flex',
                                    gap: 1,
                                    p: 0.75,
                                    border: '1px solid',
                                    borderColor: 'divider',
                                }}
                            >
                                <Button
                                    size="small"
                                    variant="contained"
                                    startIcon={aiEditLoading ? <ChaoticOrbit size="20" speed="1.5"  color='white'/> : <AssistantIcon />}
                                    onMouseDown={(event) => event.preventDefault()}
                                    onClick={editSelectionWithAi}
                                    disabled={aiEditLoading}
                                >
                                    {aiEditLoading ? localeMessages['editing'] : localeMessages['edit_with_ai']}
                                </Button>
                            </Paper>
                        </BubbleMenu>
                    )}
                    <EditorContent editor={editor} />
                    <Box
                        role="presentation"
                        onMouseDown={handleResizeStart}
                        sx={{
                            position: 'absolute',
                            bottom: 6,
                            ...(direction === 'rtl' ? { left: 8 } : { right: 8 }),
                            width: 16,
                            height: 16,
                            cursor: 'ns-resize',
                            opacity: 0.65,
                            color: 'text.secondary',
                        }}
                    >
                        <VerticalAlignCenterIcon sx={{ fontSize: 16 }} />
                    </Box>
                </Box>
            </EditorContext.Provider>
        </Paper>
    );
}

export default ContentEditor
