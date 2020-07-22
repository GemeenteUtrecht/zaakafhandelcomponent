import React, { useState } from "react";
import { Collapse } from "react-collapse";
import PropTypes from 'prop-types';

import { CheckboxInput } from './forms/Inputs';

/**
 * A single zaaktype version choice that can be selected.
 * @param  {String}  options.name     Name of the checkbox input for the form
 * @param  {String}  options.url      URL value of the zaaktype
 * @param  {String}  options.label    Label for the checkbox
 * @param  {Callback}  options.onChange Callback to invoke when the checkbox changes state
 * @param  {Boolean} options.checked  Whether the option is checked or not
 * @return {JSX}
 */
const ZaaktypeChoice = ({ name, url, label, onChange, checked=false }) => {
    return (
        <label>
            <CheckboxInput
                initial={ url }
                name={ name }
                checked={ checked }
                onChange={ onChange }
            />
            { label }
        </label>
    );
};

ZaaktypeChoice.propTypes = {
    name: PropTypes.string.isRequired,
    url: PropTypes.string.isRequired,
    label: PropTypes.string.isRequired,
    onChange: PropTypes.func.isRequired,
    checked: PropTypes.bool,
};


/**
 * A single zaaktype group containing all the different versions.
 * @return {JSX} The React component rendering a single group.
 */
const ZaaktypeGroup = ({ name, label, setChecked, versions=[], checked=[] }) => {
    const [collapsed, setCollapsed] = useState(true);
    const urls = versions.map( version => version[0] );
    const allChecked = urls.every( (url) => checked.includes(url) );
    const toggleAll = (event) => {
        const allCheckedWithoutGroupUrls = checked.filter( zaaktypeUrl => !urls.includes(zaaktypeUrl) );
        // check all the versions
        if (event.target.checked) {
            // remove all urls from this group to avoid duplicates and then add all the
            // group urls
            setChecked([...allCheckedWithoutGroupUrls, ...urls]);

        // uncheck all the versions
        } else {
            // keep all checked values except the URLs in this group
            setChecked(allCheckedWithoutGroupUrls);
        }
    };

    return (
        <li>
            <button
                type="button"
                className="zaaktype-select__btn-expand"
                onClick={ () =>  { setCollapsed(!collapsed) } }
            > { collapsed ? '+' : '-' } </button>

            <label className="zaaktype-select__group">
                <CheckboxInput
                    name="zaaktype-group"
                    initial={ label }
                    checked={ allChecked }
                    onChange={ toggleAll }
                />
                { label }
            </label>

            <Collapse isOpened={ !collapsed }>
                <ul className="zaaktype-select__items">

                    { versions.map( (version) =>
                        <li key={version[0]}>
                            <ZaaktypeChoice
                                name={name}
                                url={version[0]}
                                label={version[1]}
                                checked={ checked.includes(version[0]) }
                                onChange={ (event) => {
                                    const url = version[0];
                                    // add zaaktype
                                    if (event.target.checked) {
                                        setChecked([url, ...checked]);
                                    // remove zaaktype
                                    } else {
                                        const index = checked.indexOf(url);
                                        setChecked([...checked.splice(index, 1)]);
                                    }
                                }}
                            />
                        </li>
                    ) }
                </ul>
            </Collapse>
        </li>
    );
};

ZaaktypeGroup.propTypes = {
    name: PropTypes.string.isRequired,
    label: PropTypes.string.isRequired,
    setChecked: PropTypes.func.isRequired,
    versions: PropTypes.arrayOf(
        PropTypes.arrayOf(PropTypes.string),
    ),
    checked: PropTypes.arrayOf(PropTypes.string),
};


/**
 * A zaaktype selection allowing multiple zaaktypen to be selected, while zaaktypen
 * are grouped by version to de-clutter
 * @param  {Array}  options.zaaktypen A list of the zaaktype groups - each item is an
 *                                    array of [groupLabel, [options]] where the options
 *                                    are arrays of [value, label].
 * @param  {String} options.name      The HTML input name
 * @return {JSX}
 */
const ZaaktypeSelect = ({ zaaktypen=[], name }) => {
    const [checked, setChecked] = useState([]);

    return (
        <div className="zaaktype-select">
            <ul className="zaaktype-select__groups">
                { zaaktypen.map(
                    (group, index) => <ZaaktypeGroup
                        key={index}
                        label={group[0]}
                        versions={group[1]}
                        checked={checked}
                        setChecked={setChecked}
                        name={name}
                    />
                ) }
            </ul>
        </div>
    );
};

ZaaktypeSelect.propTypes = {
    zaaktypen: PropTypes.arrayOf(PropTypes.array),
    name: PropTypes.string.isRequired,
};

export { ZaaktypeSelect };
