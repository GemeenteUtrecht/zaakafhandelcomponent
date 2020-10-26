import React, {useContext} from 'react';
import PropTypes from 'prop-types';

import { Help } from './Help';
import { Label } from './Label';
import { ErrorList, Wrapper } from './Utils';
import {PrefixContext} from "../formsets/context";


const Select = ({
    name,
    label='',
    required=false,
    choices=[],
    id='',
    helpText='',
    classes=null,
    onChange,
    disabled=false,
    initial=null,
    value='',
    errors=[]
}) => {
    const classNames = classes ?? 'input__control input__control--select';
    const options = choices.map(([value, label], index) => {
        return (
            <option key={index} value={value}>{label}</option>
        );
    });

    const prefix = useContext(PrefixContext);
    const prefixedName = prefix ? `${prefix}-${name}` : name;
    const prefixedId = (id && prefix) ? `${prefix}-${id}` : id;

    const valueProp = initial == null ? {value: value} : {defaultValue: initial};

    const select = (
        <select
            name={prefixedName}
            id={prefixedId}
            className={classNames}
            disabled={!!disabled}
            {...valueProp}
            onChange={(event) => {
                if (onChange) {
                    onChange(event);
                }
            }}
        >
            { options }
        </select>
    );

    return (
        <Wrapper errors={errors}>
            <Label label={label} required={required} />
            <Help helpText={helpText} />
            <ErrorList errors={errors} />
            { select }
        </Wrapper>
    );
};


Select.propTypes = {
    name: PropTypes.string.isRequired,
    label: PropTypes.string,
    required: PropTypes.bool,
    choices: PropTypes.arrayOf(
        PropTypes.arrayOf(PropTypes.string),
    ),
    id: PropTypes.string,
    helpText: PropTypes.string,
    classes: PropTypes.string,
    onChange: PropTypes.func,
    disabled: PropTypes.bool,
    value: PropTypes.string,
    errors: PropTypes.arrayOf(PropTypes.string),
};


export { Select };
