/**
 * Set up search by object types.
 *
 * Selecting a certain registration displays the available object types,
 * while selecting an object type displays the relevant widget.
 */

class Search {
    constructor(node) {
        this.node = node;

        this.registrationButtons = this.bindBtnClicks();
        this.bindObjectTypeSelect();
    }

    bindBtnClicks() {
        const registrationButtons = Array.from(
            this.node
                .querySelectorAll('.search__type .btn-group .btn--choice')
        );
        registrationButtons.forEach(btn => {
            btn.addEventListener('click', () => this.onRegistrationSelect(btn));
        });
        return registrationButtons;
    }

    onRegistrationSelect(btn) {
        // deactivate all other buttons
        this.registrationButtons.forEach(_btn => _btn.classList.remove('btn--choice-selected'));
        // mark this button as activated
        btn.classList.add('btn--choice-selected');

        const activeClassName = 'search__object-types--active';

        // find the matching object type
        const oldActive = this.node.querySelector(`.${activeClassName}`);
        if (oldActive) {
            oldActive.classList.toggle(activeClassName);
        }
        const newActive = document.getElementById(btn.dataset.target);
        newActive.classList.toggle(activeClassName);
    }

    bindObjectTypeSelect() {
        const radios = this.node.querySelectorAll('.radio-select__option input');
        Array.from(radios).forEach(radio => {
            radio.addEventListener('change', event => this.onObjectTypeSelect(radio, event));
        });
    }

    onObjectTypeSelect(radio, event) {
        const selectedObjectType = event.target.value;
        const selectedRegistration = this.registrationButtons.find(
            btn => btn.classList.contains('btn--choice-selected')
        );
        const query = `object-types-${selectedRegistration.dataset.registration}-${selectedObjectType}`;
        const container = document.getElementById(query);

        const allWidgets = Array.from(this.node.querySelectorAll('.search__widget'));
        allWidgets.forEach(widget => {
            widget.classList.remove('search__widget--active');
            Array.from(widget.querySelectorAll('input')).forEach(input => {
                input.disabled = true;
                input.value = '';
            });
        });

        Array.from(container.querySelectorAll('input')).forEach(input => {
            input.disabled = false;
            input.value = '';
        });
        container.classList.add('search__widget--active');
    }
}


const searchNodes = document.querySelectorAll('.search');
Array.from(searchNodes).forEach(node => new Search(node));
