// State management
let contacts = [];
let selectedContactId = null;
let isAddingEmail = false;
let isNewContact = false;
let currentEmailList = [];
let originalContact = null;
let searchQuery = '';


// DOM Elements
const contactsList = document.getElementById('contactsList');
const contactForm = document.getElementById('contactForm');
const firstNameInput = document.getElementById('firstName');
const lastNameInput = document.getElementById('lastName');
const emailList = document.getElementById('emailList');
const addEmailBtn = document.getElementById('addEmailBtn');
const saveBtn = document.getElementById('saveBtn');
const deleteBtn = document.getElementById('deleteBtn');
const cancelBtn = document.getElementById('cancelBtn');
const addContactBtn = document.getElementById('addContactBtn');
const searchInput = document.getElementById('searchInput');

// API Functions
async function fetchContacts() {
    try {
        const response = await fetch('/api/contacts');
        contacts = await response.json();
        renderContactsList();
    } catch (error) {
        console.error('Error fetching contacts:', error);
    }
}

async function saveContact(contactData) {
    const url = contactData.id
        ? `/api/contacts/${contactData.id}`
        : '/api/contacts';

    try {
        const response = await fetch(url, {
            method: contactData.id ? 'PUT' : 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(contactData),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to save contact');
        }

        const savedContact = await response.json();
        await fetchContacts();
        selectContact(savedContact);
    } catch (error) {
        console.error('Error saving contact:', error);
        alert(error.message);
    }
}

async function deleteContact(id) {
    if (!confirm('Are you sure you want to delete this contact?')) {
        return;
    }

    try {
        const response = await fetch(`/api/contacts/${id}`, {
            method: 'DELETE',
        });

        if (!response.ok) {
            throw new Error('Failed to delete contact');
        }

        await fetchContacts();
        clearForm();
    } catch (error) {
        console.error('Error deleting contact:', error);
        alert(error.message);
    }
}

// UI Rendering Functions
function renderContactsList() {
    contactsList.innerHTML = '';

    const filteredContacts = filterContacts(contacts, searchQuery);
    const sortedContacts = [...filteredContacts].sort((a, b) =>
        a.lastName.localeCompare(b.lastName)
    );

    sortedContacts.forEach(contact => {
        const div = document.createElement('div');
        div.className = `contact-item p-4 border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer ${contact.id === selectedContactId ? 'bg-blue-50 dark:bg-gray-700' : ''
            }`;

        div.innerHTML = `
            <h3 class="text-gray-800 dark:text-white font-medium">
                ${escapeHtml(contact.firstName)} ${escapeHtml(contact.lastName)}
            </h3>
        `;
        div.addEventListener('click', () => selectContact(contact));
        contactsList.appendChild(div);
    });
}

function renderEmailList() {
    emailList.innerHTML = '';

    currentEmailList.forEach((emailObj, index) => {
        const template = document.getElementById('emailItemTemplate');
        const emailItem = template.content.cloneNode(true);

        const emailText = emailItem.querySelector('.email-text');
        emailText.id = `email-text-${index}`;
        emailText.textContent = emailObj.email;

        const deleteBtn = emailItem.querySelector('.email-delete');
        deleteBtn.id = `email-delete-${index}`;
        deleteBtn.addEventListener('click', () => {
            currentEmailList.splice(index, 1);
            renderEmailList();
            checkForChanges();
        });

        emailList.appendChild(emailItem);
    });

    if (isAddingEmail) {
        addNewEmailInput();
    }
}


function addNewEmailInput() {
    const template = document.getElementById('emailInputTemplate');
    const emailInput = template.content.cloneNode(true);
    const input = emailInput.querySelector('input');
    input.id = `email-input-${Date.now()}`;

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            const email = input.value.trim();
            if (email && isValidEmail(email)) {
                currentEmailList.push({ id: Date.now(), email });
                renderEmailList();
                if (emailInput.parentElement) {
                    emailInput.parentElement.remove();
                }
                isAddingEmail = false;
            }
            checkForChanges();
        }
    });

    input.addEventListener('input', () => {
        checkForChanges();
    });


    emailList.appendChild(emailInput);
    input.focus();
}


function selectContact(contact) {
    selectedContactId = contact.id;
    originalContact = {
        firstName: contact.firstName,
        lastName: contact.lastName,
        emails: [...contact.emails]
    };
    renderContactsList();

    contactForm.classList.remove('hidden');
    firstNameInput.value = contact.firstName;
    lastNameInput.value = contact.lastName;

    currentEmailList = [...contact.emails];
    isAddingEmail = false;
    renderEmailList();

    deleteBtn.style.display = 'block';
    checkForChanges();
}

function checkForChanges() {
    // Check for unsaved email first
    const emailInput = emailList.querySelector('input');
    const unsavedEmail = emailInput ? emailInput.value.trim() : '';
    const hasUnsavedValidEmail = unsavedEmail && isValidEmail(unsavedEmail);

    if (!originalContact) {
        // For new contacts, we just need to check if there's any data at all
        const hasData = firstNameInput.value.trim() ||
            lastNameInput.value.trim() ||
            currentEmailList.length > 0 ||
            hasUnsavedValidEmail;
        saveBtn.disabled = !hasData;
        saveBtn.classList.toggle('opacity-50', !hasData);
        return;
    }

    // For existing contacts, compare everything
    const hasChanges =
        firstNameInput.value.trim() !== originalContact.firstName ||
        lastNameInput.value.trim() !== originalContact.lastName ||
        JSON.stringify(currentEmailList.map(e => e.email)) !==
        JSON.stringify(originalContact.emails.map(e => e.email)) ||
        hasUnsavedValidEmail;

    saveBtn.disabled = !hasChanges;
    saveBtn.classList.toggle('opacity-50', !hasChanges);
}

function clearForm() {
    const isAddingNew = !selectedContactId && firstNameInput.value === '' && lastNameInput.value === '';

    selectedContactId = null;
    isNewContact = false;
    firstNameInput.value = '';
    lastNameInput.value = '';
    currentEmailList = [];
    emailList.innerHTML = '';
    isAddingEmail = false;
    deleteBtn.style.display = 'none';
    originalContact = null;
    renderEmailList();

    if (!isAddingNew) {
        contactForm.classList.add('hidden');
    }
}


// Utility Functions
function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function isValidEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

function getFormData() {
    return {
        ...(selectedContactId ? { id: selectedContactId } : {}),
        firstName: firstNameInput.value.trim(),
        lastName: lastNameInput.value.trim(),
        emails: currentEmailList
    };
}

// Search functionality
/*
* This should be modified in case of larger contact lists.
* We could pause to update ~300ms or ~1000ms after last keystroke.
* I'm not sure how React keeps track of incremental updates
*  but incremental updates would work better than updating the full DOM
*  with every keystroke.
*/
function filterContacts(contacts, query) {
    if (!query) return contacts;

    query = query.toLowerCase();
    return contacts.filter(contact => {
        const fullName = `${contact.firstName} ${contact.lastName}`.toLowerCase();
        const emails = contact.emails.map(e => e.email.toLowerCase());

        return fullName.includes(query) ||
            emails.some(email => email.includes(query));
    });
}



// Event Listeners
addEmailBtn.addEventListener('click', (e) => {
    e.preventDefault();
    if (!isAddingEmail) {
        isAddingEmail = true;
        if (isNewContact) {
            renderEmailList([]);
        } else {
            const contact = contacts.find(c => c.id === selectedContactId);
            if (contact) {
                renderEmailList(contact.emails);
            }
        }
    }
});

addContactBtn.addEventListener('click', () => {
    clearForm();
    isNewContact = true;
    contactForm.classList.remove('hidden');
});


saveBtn.addEventListener('click', async (e) => {
    e.preventDefault();

    // Check for unsaved email in input field
    const emailInput = emailList.querySelector('input');
    if (emailInput) {
        const email = emailInput.value.trim();
        if (email && isValidEmail(email)) {
            currentEmailList.push({ id: Date.now(), email });
        }
    }

    const contactData = getFormData();
    await saveContact(contactData);
});


deleteBtn.addEventListener('click', async (e) => {
    e.preventDefault();
    if (selectedContactId) {
        await deleteContact(selectedContactId);
    }
});

cancelBtn.addEventListener('click', (e) => {
    e.preventDefault();
    clearForm();
});

firstNameInput.addEventListener('input', checkForChanges);
lastNameInput.addEventListener('input', checkForChanges);

searchInput.addEventListener('input', (e) => {
    searchQuery = e.target.value;
    renderContactsList();
});


// Initialize
document.addEventListener('DOMContentLoaded', () => {
    fetchContacts();
    clearForm();
    contactForm.classList.add('hidden');
});
