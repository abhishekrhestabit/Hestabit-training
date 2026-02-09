import "./globals.css";
import Navbar from "../components/Navbar";

const Home = ({children}) => {
  return (
    <html lang="en">
    <body> 
      <Navbar></Navbar>

      <main className="w-screen">{children}</main>
    </body>
    </html>
  );
}

export default Home;