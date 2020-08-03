const getAuthorName = (user) => {
    const lastName = user.last_name ?? user.lastName;
    const firstName = user.first_name ?? user.firstName;
    return lastName ? `${firstName} ${lastName}` : user.username;
};

export { getAuthorName };
