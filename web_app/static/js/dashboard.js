// Agent Trace Viewer JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Add smooth scrolling for timeline navigation
    initializeTimelineNavigation();
    
    // Add keyboard shortcuts
    initializeKeyboardShortcuts();
    
    // Initialize copy functionality
    initializeCopyButtons();
    renderMarkdownResults();
});

// Toggle collapsible sections
function toggleSection(header) {
    const content = header.nextElementSibling;
    const icon = header.querySelector('.toggle-icon');
    
    if (content.style.display === 'none') {
        content.style.display = 'block';
        icon.classList.remove('fa-chevron-right');
        icon.classList.add('fa-chevron-down');
    } else {
        content.style.display = 'none';
        icon.classList.remove('fa-chevron-down');
        icon.classList.add('fa-chevron-right');
    }
}

// Toggle LLM Request display
function toggleLLMRequest(button, step) {
    const content = document.getElementById(`llm-request-${step}`);
    if (content.style.display === 'none') {
        content.style.display = 'block';
        button.innerHTML = '<i class="fas fa-code"></i> Hide LLM Request';
    } else {
        content.style.display = 'none';
        button.innerHTML = '<i class="fas fa-code"></i> View LLM Request';
    }
}

// Show full content in modal
function showFullContent(content) {
    const modal = document.getElementById('fullContentModal');
    const modalContent = document.getElementById('fullContentPre');
    modalContent.textContent = content;
    
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

// Initialize timeline navigation
function initializeTimelineNavigation() {
    // Add click handlers to timeline markers for smooth scrolling
    const markers = document.querySelectorAll('.timeline-marker');
    markers.forEach(marker => {
        marker.style.cursor = 'pointer';
        marker.addEventListener('click', function() {
            const card = this.closest('.timeline-card');
            card.scrollIntoView({
                behavior: 'smooth',
                block: 'center'
            });
            
            // Add highlight effect
            card.classList.add('highlight');
            setTimeout(() => {
                card.classList.remove('highlight');
            }, 1500);
        });
    });
}

// Initialize keyboard shortcuts
function initializeKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + K to focus on file dropdown
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            document.getElementById('fileDropdown').click();
        }
        
        // Arrow keys to navigate between timeline cards
        if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
            const cards = Array.from(document.querySelectorAll('.timeline-card'));
            const focused = document.activeElement.closest('.timeline-card');
            
            if (focused) {
                const currentIndex = cards.indexOf(focused);
                let newIndex;
                
                if (e.key === 'ArrowDown') {
                    newIndex = Math.min(currentIndex + 1, cards.length - 1);
                } else {
                    newIndex = Math.max(currentIndex - 1, 0);
                }
                
                cards[newIndex].scrollIntoView({
                    behavior: 'smooth',
                    block: 'center'
                });
                cards[newIndex].focus();
            } else if (cards.length > 0) {
                cards[0].focus();
            }
        }
        
        // 'e' to expand all sections
        if (e.key === 'e' && !e.ctrlKey && !e.metaKey) {
            expandAllSections();
        }
        
        // 'c' to collapse all sections
        if (e.key === 'c' && !e.ctrlKey && !e.metaKey) {
            collapseAllSections();
        }
    });
}

// Expand all collapsible sections
function expandAllSections() {
    const toggleableHeaders = document.querySelectorAll('.context-header, .params-header, .output-header');
    toggleableHeaders.forEach(header => {
        const content = header.nextElementSibling;
        const icon = header.querySelector('.toggle-icon');
        
        if (content && content.style.display === 'none') {
            content.style.display = 'block';
            if (icon) {
                icon.classList.remove('fa-chevron-right');
                icon.classList.add('fa-chevron-down');
            }
        }
    });
}

// Collapse all collapsible sections
function collapseAllSections() {
    const toggleableHeaders = document.querySelectorAll('.context-header, .params-header, .output-header');
    toggleableHeaders.forEach(header => {
        const content = header.nextElementSibling;
        const icon = header.querySelector('.toggle-icon');
        
        if (content && content.style.display !== 'none') {
            content.style.display = 'none';
            if (icon) {
                icon.classList.remove('fa-chevron-down');
                icon.classList.add('fa-chevron-right');
            }
        }
    });
}

// Render markdown content in task result sections
function renderMarkdownResults() {
    if (typeof marked === 'undefined') {
        console.warn('marked.js not loaded, skipping markdown rendering.');
        return;
    }

    const markdownElements = document.querySelectorAll('.task-result-markdown');
    markdownElements.forEach(el => {
        const rawMarkdown = el.textContent;
        el.innerHTML = marked.parse(rawMarkdown);
    });
}

// Initialize copy buttons functionality
function initializeCopyButtons() {
    // Add copy functionality to code blocks
    const codeBlocks = document.querySelectorAll('.tool-output, .context-display, .message-content');
    
    codeBlocks.forEach(block => {
        // Create copy button
        const wrapper = document.createElement('div');
        wrapper.style.position = 'relative';
        block.parentNode.insertBefore(wrapper, block);
        wrapper.appendChild(block);
        
        const copyBtn = document.createElement('button');
        copyBtn.className = 'copy-btn';
        copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
        copyBtn.title = 'Copy to clipboard';
        copyBtn.style.cssText = `
            position: absolute;
            top: 0.5rem;
            right: 0.5rem;
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: #94a3b8;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.875rem;
            transition: all 0.2s;
            z-index: 10;
        `;
        
        wrapper.appendChild(copyBtn);
        
        copyBtn.addEventListener('click', function() {
            const text = block.textContent;
            navigator.clipboard.writeText(text).then(() => {
                copyBtn.innerHTML = '<i class="fas fa-check"></i>';
                copyBtn.style.color = '#10b981';
                
                setTimeout(() => {
                    copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
                    copyBtn.style.color = '#94a3b8';
                }, 2000);
            });
        });
        
        // Show/hide on hover
        wrapper.addEventListener('mouseenter', () => {
            copyBtn.style.opacity = '1';
        });
        
        wrapper.addEventListener('mouseleave', () => {
            copyBtn.style.opacity = '0.5';
        });
        
        copyBtn.style.opacity = '0.5';
    });
}

// Add highlight animation
const style = document.createElement('style');
style.textContent = `
    .timeline-card.highlight {
        animation: highlightPulse 1.5s ease-out;
    }
    
    @keyframes highlightPulse {
        0% {
            box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.4);
        }
        70% {
            box-shadow: 0 0 0 10px rgba(99, 102, 241, 0);
        }
        100% {
            box-shadow: 0 0 0 0 rgba(99, 102, 241, 0);
        }
    }
    
    .copy-btn:hover {
        background: rgba(255, 255, 255, 0.2) !important;
        transform: translateY(-1px);
    }
`;
document.head.appendChild(style);

// Export functions for potential external use
window.DashboardUtils = {
    toggleSection,
    toggleLLMRequest,
    showFullContent,
    expandAllSections,
    collapseAllSections
};