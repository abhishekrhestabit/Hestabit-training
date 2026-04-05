
const Button = ({ onClick, variant = "primary", children, className = "" }) => {

    const variants = {
        primary: "bg-blue-500 hover:bg-blue-600 text-white",
        secondary: "bg-gray-500 hover:bg-gray-600 text-white",
        danger: "bg-red-500 hover:bg-red-600 text-white",
      };


  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 ${variants[variant]} rounded focus:outline-none ${className}`}
    >
      {children}
    </button>
  );
};

export default Button;