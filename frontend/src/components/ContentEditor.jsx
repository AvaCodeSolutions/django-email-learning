import './styles.scss'

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
    Button,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    TextField,
    Typography,
    Alert
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
        availableFeatures = [],
    } = useAppContext();
    const direction = defaultDirection || appDirection;
    const configuredAiModel = aiTextEditModel || aiTextEditingModel;
    const hasAiPermission = userRole === 'admin' || userRole === 'editor';
    const hasAiFeatureEnabled = Boolean(configuredAiModel) && availableFeatures.includes('ai_edit');
    const aiBaseUrl = apiBaseUrl?.includes('/api/platform')
        ? apiBaseUrl.replace('/api/platform', '/api/ai')
        : '/email_learning/api/ai';
    const defaultTextAlign = direction === 'rtl' ? 'right' : 'left';
    const minHeight = 200 + (Math.max(0, extraMinLines) * 24);
    const [editorHeight, setEditorHeight] = useState(minHeight);
    const [aiEditLoading, setAiEditLoading] = useState(false);
    const [aiSuggestion, setAiSuggestion] = useState(null);
    const [aiEditError, setAiEditError] = useState(null);
    const [isImageDialogOpen, setIsImageDialogOpen] = useState(false);
    const [imageFormValues, setImageFormValues] = useState({ src: '', alt: '' });

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

    // Abandon a pending AI suggestion (without applying it) if the user moves
    // their selection elsewhere before accepting or rejecting it.
    useEffect(() => {
        if (!editor) {
            return;
        }
        const handleSelectionUpdate = ({ editor: activeEditor }) => {
            setAiSuggestion((current) => {
                if (!current) {
                    return current;
                }
                const { from, to } = activeEditor.state.selection;
                return from === current.from && to === current.to ? current : null;
            });
        };
        editor.on('selectionUpdate', handleSelectionUpdate);
        return () => {
            editor.off('selectionUpdate', handleSelectionUpdate);
        };
    }, [editor]);

    // The AI-edit bubble menu's content changes size (button vs. suggestion
    // preview vs. error), but resizing it doesn't produce a ProseMirror
    // transaction, so floating-ui never recomputes its position on its own.
    // Nudge it explicitly whenever the content that's shown might have changed.
    useEffect(() => {
        if (!editor) {
            return;
        }
        editor.view.dispatch(editor.state.tr.setMeta('ai-edit-bubble-menu', 'updatePosition'));
    }, [editor, aiSuggestion, aiEditLoading, aiEditError]);

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

    const openImageEditDialog = () => {
        const { src, alt } = editor.getAttributes('image');
        setImageFormValues({ src: src ?? '', alt: alt ?? '' });
        setIsImageDialogOpen(true);
    };

    const closeImageEditDialog = () => {
        setIsImageDialogOpen(false);
    };

    const handleImageFieldChange = (field) => (event) => {
        const { value } = event.target;
        setImageFormValues((previousValues) => ({
            ...previousValues,
            [field]: value,
        }));
    };

    const saveImageAttributes = () => {
        const normalizedSrc = imageFormValues.src.trim();
        const normalizedAlt = imageFormValues.alt.trim();

        if (!normalizedSrc) {
            return;
        }

        editor
            .chain()
            .focus()
            .updateAttributes('image', {
                src: normalizedSrc,
                alt: normalizedAlt,
            })
            .run();

        closeImageEditDialog();
    };

    const getActiveOrganizationId = () => {
        if (typeof window === 'undefined') {
            return null;
        }
        return window.localStorage.getItem('activeOrganizationId');
    };

    // Top-level (direct child of doc) node types the AI is allowed to rewrite.
    // Anything else (images, code blocks, etc.) is left alone, since a
    // rewritten image/code block wouldn't make sense.
    const AI_EDITABLE_TOP_LEVEL_NODE_TYPES = new Set(['paragraph', 'heading', 'bulletList', 'blockquote']);

    // The top-level doc nodes that the [from, to) range overlaps at all, with
    // each node's own outer position range (including its own tags).
    const getOverlappingTopLevelNodes = (doc, from, to) => {
        const nodes = [];
        doc.forEach((node, offset) => {
            const start = offset;
            const end = offset + node.nodeSize;
            if (end <= from || start >= to) {
                return;
            }
            nodes.push({ node, start, end });
        });
        return nodes;
    };

    // Whether [from, to) exactly covers the full text of one or more
    // contiguous top-level nodes, all of editable types. Text (rather than
    // raw position) comparison is used at the edges so this also matches
    // nodes like blockquote whose visible text sits one level deeper than
    // the node's own boundary (inside its wrapped paragraph).
    const getWholeTopLevelBlocksSelected = (doc, from, to) => {
        const nodes = getOverlappingTopLevelNodes(doc, from, to);
        if (nodes.length === 0) {
            return null;
        }
        if (!nodes.every(({ node }) => AI_EDITABLE_TOP_LEVEL_NODE_TYPES.has(node.type.name))) {
            return null;
        }

        const first = nodes[0];
        const last = nodes[nodes.length - 1];
        const firstFullText = doc.textBetween(first.start + 1, first.end - 1, '\n', '\n');
        const firstSelectedText = doc.textBetween(
            Math.max(from, first.start + 1),
            Math.min(to, first.end - 1),
            '\n',
            '\n',
        );
        if (firstSelectedText !== firstFullText) {
            return null;
        }

        const lastFullText = doc.textBetween(last.start + 1, last.end - 1, '\n', '\n');
        const lastSelectedText = doc.textBetween(
            Math.max(from, last.start + 1),
            Math.min(to, last.end - 1),
            '\n',
            '\n',
        );
        if (lastSelectedText !== lastFullText) {
            return null;
        }

        return { start: first.start, end: last.end };
    };

    const getSelectedTextForAi = (activeEditor) => {
        const { selection, doc } = activeEditor.state;
        const { from, to, empty } = selection;
        if (empty) {
            return null;
        }

        const selectedText = doc.textBetween(from, to, '\n', '\n');
        const normalizedText = selectedText.trim();
        const isWithinCharLimit = normalizedText.length >= 40 && normalizedText.length <= 1000;
        const wholeBlocksRange = getWholeTopLevelBlocksSelected(doc, from, to);

        if (!isWithinCharLimit || !wholeBlocksRange) {
            return null;
        }

        // Replace the full nodes (including their own tags), not just their
        // inner content, so this works the same whether one or several
        // blocks are selected.
        const { start: replaceFrom, end: replaceTo } = wholeBlocksRange;
        const serializer = DOMSerializer.fromSchema(activeEditor.state.schema);
        const wrapper = document.createElement('div');
        wrapper.appendChild(serializer.serializeFragment(doc.slice(replaceFrom, replaceTo).content));
        const textWithMarkup = wrapper.innerHTML.trim();

        return {
            from,
            to,
            replaceFrom,
            replaceTo,
            text: normalizedText,
            textWithMarkup,
        };
    };

    const isSuggestionForCurrentSelection = (activeEditor) => {
        if (!aiSuggestion) {
            return false;
        }
        const { from, to } = activeEditor.state.selection;
        return from === aiSuggestion.from && to === aiSuggestion.to;
    };

    const canShowAiEditBubbleMenu = (activeEditor) => {
        if (isSuggestionForCurrentSelection(activeEditor)) {
            return true;
        }
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

    // Renders the AI suggestion as plain text (no raw HTML injection, since
    // the AI response is untrusted), but keeps block structure visible by
    // inserting line breaks between blocks and bullets for list items.
    const getPlainTextPreview = (html) => {
        if (typeof html !== 'string') {
            return '';
        }
        const wrapper = document.createElement('div');
        wrapper.innerHTML = html;

        if (wrapper.children.length === 0) {
            return wrapper.textContent || wrapper.innerText || '';
        }

        const blockTexts = [...wrapper.children].map((child) => {
            if (child.tagName === 'UL' || child.tagName === 'OL') {
                return [...child.children].map((item) => `• ${item.textContent.trim()}`).join('\n');
            }
            return child.textContent.trim();
        });

        return blockTexts.join('\n\n');
    };

    const acceptAiSuggestion = () => {
        if (!aiSuggestion) {
            return;
        }
        const { replaceFrom, replaceTo, editedHtml } = aiSuggestion;
        editor
            .chain()
            .focus()
            .insertContentAt({ from: replaceFrom, to: replaceTo }, editedHtml)
            .run();
        setAiSuggestion(null);
    };

    const rejectAiSuggestion = () => {
        setAiSuggestion(null);
    };

    const editSelectionWithAi = async () => {
        const selection = getSelectedTextForAi(editor);
        const organizationId = getActiveOrganizationId();
        if (!selection || !organizationId || aiEditLoading) {
            return;
        }

        setAiEditLoading(true);
        setAiEditError(null);
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
                const knownErrorMessages = {
                    input_too_long: localeMessages['ai_edit_error_too_long'],
                    input_too_short: localeMessages['ai_edit_error_too_short'],
                };
                setAiEditError(knownErrorMessages[data.error] || localeMessages['ai_edit_error']);
                return;
            }

            // Don't apply the edit yet - show it to the user for review first,
            // and only replace the selection if they explicitly accept it.
            setAiSuggestion({
                from: selection.from,
                to: selection.to,
                replaceFrom: selection.replaceFrom,
                replaceTo: selection.replaceTo,
                editedHtml: data.edited_text.trim(),
            });
        } catch (error) {
            console.error('AI text editing request failed:', error);
            setAiEditError(localeMessages['ai_edit_error']);
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
                    zIndex: 10,
                    flexWrap: 'wrap',
                    height: 'auto',
                    minHeight: 'unset',
                    py: 0.5,
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
                            appendTo={() => document.body}
                            style={{ zIndex: 1500 }}
                            getReferencedVirtualElement={() => {
                                if (!editor) {
                                    return null;
                                }
                                const { from, to } = editor.state.selection;
                                const top = Math.min(
                                    editor.view.coordsAtPos(from).top,
                                    editor.view.coordsAtPos(to).top,
                                );
                                return {
                                    getBoundingClientRect: () => ({
                                        x: 0,
                                        y: top,
                                        top,
                                        bottom: top,
                                        left: 0,
                                        right: window.innerWidth,
                                        width: window.innerWidth,
                                        height: 0,
                                    }),
                                };
                            }}
                            options={{
                                duration: 0,
                                placement: 'top',
                                animation: false,
                                delay: [0, 0],
                                zIndex: 1500,
                                strategy: 'fixed',
                                shift: { padding: 16 },
                            }}
                        >
                            <Paper
                                elevation={2}
                                sx={{
                                    position: 'relative',
                                    zIndex: 1500,
                                    p: 2,
                                    border: '1px solid',
                                    borderColor: 'divider',
                                    maxWidth: 'min(480px, calc(100vw - 32px))',
                                }}
                            >
                                {aiSuggestion ? (
                                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75 }}>
                                        <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.secondary' }}>
                                            {localeMessages['ai_suggestion_label']}
                                        </Typography>
                                        <Typography
                                            variant="body2"
                                            sx={{
                                                display: 'block',
                                                backgroundColor: '#f6f7f7',
                                                padding: '10px',
                                                borderRadius: '10px',
                                                maxHeight: 160,
                                                overflowY: 'auto',
                                                whiteSpace: 'pre-wrap',
                                            }}
                                        >
                                            {getPlainTextPreview(aiSuggestion.editedHtml)}
                                        </Typography>
                                        <Typography variant="caption" color="text.secondary">
                                            {localeMessages['ai_suggestion_review_note']}
                                        </Typography>
                                        <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end', mt: 0.5 }}>
                                            <Button
                                                size="small"
                                                onMouseDown={(event) => event.preventDefault()}
                                                onClick={rejectAiSuggestion}
                                            >
                                                {localeMessages['ai_edit_reject']}
                                            </Button>
                                            <Button
                                                size="small"
                                                variant="contained"
                                                onMouseDown={(event) => event.preventDefault()}
                                                onClick={acceptAiSuggestion}
                                            >
                                                {localeMessages['ai_edit_accept']}
                                            </Button>
                                        </Box>
                                    </Box>
                                ) : (
                                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                                        <Button
                                            size="small"
                                            variant="contained"
                                            startIcon={aiEditLoading ? <ChaoticOrbit size="20" speed="1.5"  color='white'/> : <AssistantIcon />}
                                            onMouseDown={(event) => event.preventDefault()}
                                            onClick={editSelectionWithAi}
                                            disabled={aiEditLoading}
                                            sx={{ alignSelf: 'flex-start' }}
                                        >
                                            {aiEditLoading ? localeMessages['editing'] : localeMessages['edit_with_ai']}
                                        </Button>
                                        {aiEditError && (
                                            <Alert severity="error" sx={{ py: 0 }} onClose={() => setAiEditError(null)}>
                                                {aiEditError}
                                            </Alert>
                                        )}
                                    </Box>
                                )}
                            </Paper>
                        </BubbleMenu>
                    )}
                    {!disabled && (
                        <BubbleMenu
                            pluginKey="image-bubble-menu"
                            editor={editor}
                            shouldShow={({ editor: activeEditor }) => (
                                activeEditor.isFocused && activeEditor.isActive('image')
                            )}
                            updateDelay={0}
                            options={{
                                duration: 0,
                                placement: 'top',
                                animation: false,
                                zIndex: 2500,
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
                                    startIcon={<ImageIcon />}
                                    onMouseDown={(event) => event.preventDefault()}
                                    onClick={openImageEditDialog}
                                >
                                    Edit Image
                                </Button>
                            </Paper>
                        </BubbleMenu>
                    )}
                    <EditorContent editor={editor} />
                    <Dialog
                        open={isImageDialogOpen}
                        onClose={closeImageEditDialog}
                        fullWidth
                        maxWidth="sm"
                    >
                        <DialogTitle>Edit Image</DialogTitle>
                        <DialogContent>
                            <TextField
                                autoFocus
                                margin="dense"
                                label="Image URL"
                                type="url"
                                fullWidth
                                value={imageFormValues.src}
                                onChange={handleImageFieldChange('src')}
                            />
                            <TextField
                                margin="dense"
                                label="Alt text"
                                fullWidth
                                value={imageFormValues.alt}
                                onChange={handleImageFieldChange('alt')}
                            />
                        </DialogContent>
                        <DialogActions>
                            <Button onClick={closeImageEditDialog}>Cancel</Button>
                            <Button onClick={saveImageAttributes} disabled={!imageFormValues.src.trim()} variant="contained">
                                Save
                            </Button>
                        </DialogActions>
                    </Dialog>
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
