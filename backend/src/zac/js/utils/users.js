import { get } from './fetch';

const getUserName = (user) => {
    const lastName = user.last_name ?? user.lastName;
    const firstName = user.first_name ?? user.firstName;
    return lastName ? `${firstName} ${lastName}` : user.username;
};

const fetchUsers = async ( {inputValue, excludedUsers = [], ENDPOINT}) => {
    const response = await get(ENDPOINT, { search: inputValue }, excludedUsers);
    const { results } = response;
    return results.map((user) => ({
        value: user.id,
        label: getUserName(user),
        userObject: user,
    }));
}

export { getUserName, fetchUsers };
